"""Unit tests for the question-answering MVP. No database, no LLM, no network.

Run from this directory:
    python -m pytest test_qa_app.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from janus.llm import LlmConfig, LlmError

sys.path.insert(0, str(Path(__file__).resolve().parent))

import qa_app  # noqa: E402
from qa_app import (  # noqa: E402
    QaError,
    answer,
    build_app,
    build_context,
    draft_sql,
    fetch_schema,
    run_query,
)

JANUS = "http://janus.test"
LLM = LlmConfig(base_url="http://llm.test/v1", model="m")


class Response:
    def __init__(self, status_code: int, body=None):
        self.status_code = status_code
        self._body = body
        self.content = b"" if body is None else b"{}"

    def json(self):
        return self._body


class FakeHttp:
    """Answers GET and POST by URL suffix; records every call."""

    def __init__(self, routes: dict[str, Response]):
        self.routes = routes
        self.calls: list[dict] = []

    def _route(self, url: str) -> Response:
        for suffix, response in self.routes.items():
            if url.endswith(suffix):
                return response
        raise AssertionError(f"no route for {url}")

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"method": "GET", "url": url, "headers": headers or {}})
        return self._route(url)

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(
            {"method": "POST", "url": url, "json": json, "headers": headers or {}}
        )
        return self._route(url)


def _models_listing():
    return Response(
        200,
        {
            "models": [
                {"name": "orders", "column_count": 3, "certified": True},
                {"name": "scratch", "column_count": 1, "certified": False},
            ]
        },
    )


def _orders_detail():
    return Response(
        200,
        {
            "name": "orders",
            "primary_key": "order_id",
            "certified": True,
            "columns": [
                {"name": "order_id", "type": "INT"},
                {"name": "amount", "type": "DECIMAL"},
            ],
        },
    )


def _query_result(rows):
    return Response(
        200,
        {
            "columns": ["order_id"],
            "rows": rows,
            "row_count": len(rows),
            "truncated": False,
            "provenance": {
                "models": ["orders"],
                "role": "analyst",
                "expanded_sql": "SELECT ...",
            },
        },
    )


# ── fetch_schema ────────────────────────────────────────────────────────────


def test_fetch_schema_keeps_only_certified_models():
    http = FakeHttp({"/models": _models_listing(), "/models/orders": _orders_detail()})
    models = fetch_schema(JANUS, "tok", http)
    assert [m["name"] for m in models] == ["orders"]
    detail_calls = [c for c in http.calls if c["url"].endswith("/models/orders")]
    assert detail_calls and detail_calls[0]["headers"] == {
        "Authorization": "Bearer tok"
    }


def test_fetch_schema_passes_a_refusal_through():
    http = FakeHttp({"/models": Response(401, {"error": "missing bearer token"})})
    with pytest.raises(QaError) as exc:
        fetch_schema(JANUS, None, http)
    assert exc.value.status == 401


def test_fetch_schema_fails_when_nothing_is_certified():
    listing = Response(200, {"models": [{"name": "scratch", "certified": False}]})
    with pytest.raises(QaError) as exc:
        fetch_schema(JANUS, "tok", FakeHttp({"/models": listing}))
    assert exc.value.status == 404


# ── context and drafting ────────────────────────────────────────────────────


def test_context_lists_each_model_with_its_columns_and_key():
    text = build_context([_orders_detail().json()])
    assert text == "- orders (primary key: order_id): order_id INT, amount DECIMAL"


def test_draft_accepts_one_select_and_strips_the_semicolon(monkeypatch):
    monkeypatch.setattr(
        qa_app, "complete_json", lambda *a, **k: {"sql": "SELECT order_id FROM orders;"}
    )
    assert draft_sql(LLM, "q", "ctx") == "SELECT order_id FROM orders"


@pytest.mark.parametrize(
    "bad_sql",
    [
        "DELETE FROM orders",
        "SELECT 1; DROP TABLE orders",
        "UPDATE orders SET amount = 0",
    ],
)
def test_draft_refuses_anything_but_one_select(monkeypatch, bad_sql):
    monkeypatch.setattr(qa_app, "complete_json", lambda *a, **k: {"sql": bad_sql})
    with pytest.raises(QaError) as exc:
        draft_sql(LLM, "q", "ctx")
    assert exc.value.status == 422


def test_draft_reports_when_the_model_cannot_answer(monkeypatch):
    monkeypatch.setattr(qa_app, "complete_json", lambda *a, **k: {"sql": None})
    with pytest.raises(QaError) as exc:
        draft_sql(LLM, "q", "ctx")
    assert exc.value.status == 422


def test_draft_turns_an_llm_failure_into_503(monkeypatch):
    def boom(*a, **k):
        raise LlmError("timeout")

    monkeypatch.setattr(qa_app, "complete_json", boom)
    with pytest.raises(QaError) as exc:
        draft_sql(LLM, "q", "ctx")
    assert exc.value.status == 503


# ── running the query ───────────────────────────────────────────────────────


def test_run_query_sends_the_token_and_returns_the_body():
    http = FakeHttp({"/query": _query_result([{"order_id": 101}])})
    body = run_query(JANUS, "tok", "SELECT order_id FROM orders", http=http)
    assert body["rows"] == [{"order_id": 101}]
    sent = http.calls[-1]
    assert sent["headers"] == {"Authorization": "Bearer tok"}
    assert sent["json"]["sql"] == "SELECT order_id FROM orders"


def test_run_query_raises_janus_refusal_with_its_status():
    http = FakeHttp({"/query": Response(422, {"error": "Permission Denied"})})
    with pytest.raises(QaError) as exc:
        run_query(JANUS, "tok", "SELECT amount FROM orders", http=http)
    assert exc.value.status == 422
    assert "Permission Denied" in str(exc.value)


# ── the whole flow ──────────────────────────────────────────────────────────


def _http_for_flow(rows):
    return FakeHttp(
        {
            "/models": _models_listing(),
            "/models/orders": _orders_detail(),
            "/query": _query_result(rows),
        }
    )


def test_answer_runs_the_drafted_sql_through_janus_with_the_callers_token():
    http = _http_for_flow([{"order_id": 101}, {"order_id": 102}])
    seen = {}

    def draft(llm, question, context):
        seen["context"] = context
        return "SELECT order_id FROM orders"

    result = answer(
        "which orders are mine?",
        janus_url=JANUS,
        token="tok",
        llm=LLM,
        http=http,
        draft=draft,
    )
    assert "orders" in seen["context"] and "scratch" not in seen["context"]
    assert result["sql"] == "SELECT order_id FROM orders"
    assert result["rows"] == [{"order_id": 101}, {"order_id": 102}]
    assert result["row_count"] == 2
    assert result["provenance"]["role"] == "analyst"
    query_call = [c for c in http.calls if c["method"] == "POST"][0]
    assert query_call["headers"] == {"Authorization": "Bearer tok"}


def test_answer_rejects_an_empty_question_before_any_call():
    http = _http_for_flow([])
    with pytest.raises(QaError) as exc:
        answer(
            "   ",
            janus_url=JANUS,
            token="tok",
            llm=LLM,
            http=http,
            draft=lambda *a: "SELECT 1",
        )
    assert exc.value.status == 400
    assert http.calls == []


def test_answer_does_not_run_sql_the_draft_refused():
    http = _http_for_flow([])

    def draft(llm, question, context):
        raise QaError("only a single SELECT statement is accepted", 422)

    with pytest.raises(QaError):
        answer("drop it", janus_url=JANUS, token="tok", llm=LLM, http=http, draft=draft)
    assert not [c for c in http.calls if c["method"] == "POST"]


# ── the HTTP wrapper ────────────────────────────────────────────────────────


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        qa_app, "draft_sql", lambda llm, q, ctx: "SELECT order_id FROM orders"
    )
    http = _http_for_flow([{"order_id": 101}])
    return TestClient(build_app(janus_url=JANUS, llm=LLM, http=http))


def test_ask_needs_a_bearer_token(client):
    r = client.post("/ask", json={"question": "orders?"})
    assert r.status_code == 401


def test_ask_returns_the_answer(client):
    r = client.post(
        "/ask", json={"question": "orders?"}, headers={"Authorization": "Bearer tok"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["rows"] == [{"order_id": 101}]


def test_ask_reports_an_empty_question_as_400(client):
    r = client.post(
        "/ask", json={"question": ""}, headers={"Authorization": "Bearer tok"}
    )
    assert r.status_code == 400


def test_ask_rejects_a_question_that_is_not_text(client):
    r = client.post(
        "/ask", json={"question": 5}, headers={"Authorization": "Bearer tok"}
    )
    assert r.status_code == 400
