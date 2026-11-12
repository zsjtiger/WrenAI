"""Model-backed column descriptions with the deterministic fallback.

A real HTTP server stands in for an OpenAI-compatible endpoint, so the request
and response handling in janus.llm runs as it would against a live model.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from janus.connector.factory import get_connector
from janus.context_draft import (
    DESCRIPTION_SOURCE,
    deterministic_description,
    generate_drafts,
)
from janus.llm import LlmConfig, LlmError, complete_json, load_llm_config
from janus.model.data_source import DataSource
from tests.unit.conftest import shop_connection_info

pytestmark = pytest.mark.unit


class _Endpoint:
    """Serves one canned reply and records every request body it receives."""

    def __init__(self) -> None:
        self.status = 200
        self.reply: str | None = None  # content of the assistant message
        self.raw_body: bytes | None = None  # overrides the whole response body
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - http.server API
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                endpoint.requests.append(json.loads(body))
                endpoint.headers.append(dict(self.headers))
                if endpoint.raw_body is not None:
                    payload = endpoint.raw_body
                else:
                    payload = json.dumps(
                        {"choices": [{"message": {"content": endpoint.reply}}]}
                    ).encode()
                self.send_response(endpoint.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):  # keep test output quiet
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}/v1"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()

    def config(self, api_key: str | None = None) -> LlmConfig:
        return LlmConfig(
            base_url=self.url, model="test-model", api_key=api_key, timeout=5
        )


@pytest.fixture
def connector(shop_dir):
    info = DataSource.duckdb.get_connection_info(shop_connection_info(shop_dir))
    conn = get_connector(DataSource.duckdb, info)
    yield conn
    conn.close()


def _column(model: dict, name: str) -> dict:
    return next(c for c in model["columns"] if c["name"] == name)


def _drafts(project, connector, **kwargs):
    """Generate drafts and return ``(models_by_name, DraftResult)``."""
    import yaml  # noqa: PLC0415

    result = generate_drafts(project, connector, DataSource.duckdb, **kwargs)
    models = {}
    for name in ("customers", "orders"):
        path = project / "draft" / "models" / name / "metadata.yml"
        models[name] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return models, result


# ── configuration ────────────────────────────────────────────────────────────


def test_no_configuration_means_no_model():
    assert load_llm_config({}) is None
    assert load_llm_config({"JANUS_LLM_BASE_URL": "http://x"}) is None
    assert load_llm_config({"JANUS_LLM_MODEL": "m"}) is None


def test_configuration_is_read_from_the_environment():
    config = load_llm_config(
        {
            "JANUS_LLM_BASE_URL": "https://example.test/v1/",
            "JANUS_LLM_MODEL": "m",
            "JANUS_LLM_API_KEY": "k",
        }
    )
    assert config == LlmConfig(
        base_url="https://example.test/v1", model="m", api_key="k"
    )


# ── the client ───────────────────────────────────────────────────────────────


def test_client_sends_the_key_as_a_bearer_token():
    with _Endpoint() as endpoint:
        endpoint.reply = '{"ok": true}'
        assert complete_json(endpoint.config("secret"), "sys", "user") == {"ok": True}
    assert endpoint.headers[0]["Authorization"] == "Bearer secret"


def test_client_accepts_a_fenced_json_reply():
    with _Endpoint() as endpoint:
        endpoint.reply = '```json\n{"a": 1}\n```'
        assert complete_json(endpoint.config(), "sys", "user") == {"a": 1}


def test_http_error_raises_without_leaking_the_key():
    with _Endpoint() as endpoint:
        endpoint.status = 401
        endpoint.reply = "{}"
        with pytest.raises(LlmError, match="HTTP 401") as exc:
            complete_json(endpoint.config("super-secret-key"), "sys", "user")
    assert "super-secret-key" not in str(exc.value)


def test_non_json_reply_raises():
    with _Endpoint() as endpoint:
        endpoint.reply = "I cannot help with that."
        with pytest.raises(LlmError, match="valid JSON"):
            complete_json(endpoint.config(), "sys", "user")


def test_unreachable_endpoint_raises():
    config = LlmConfig(base_url="http://127.0.0.1:1/v1", model="m", timeout=2)
    with pytest.raises(LlmError, match="unreachable"):
        complete_json(config, "sys", "user")


# ── draft descriptions ───────────────────────────────────────────────────────


def test_model_descriptions_are_used_and_marked_llm(make_project, connector):
    with _Endpoint() as endpoint:
        endpoint.reply = json.dumps(
            {
                "descriptions": {
                    "id": "Unique customer identifier.",
                    "name": "Customer's display name.",
                }
            }
        )
        project = make_project([])
        drafts, _ = _drafts(
            project,
            connector,
            suggest_terms=True,
            llm=endpoint.config(),
        )
    cust = drafts["customers"]
    assert _column(cust, "id")["description"] == "Unique customer identifier."
    assert _column(cust, "id")["properties"][DESCRIPTION_SOURCE] == "llm"


def test_the_model_sees_names_and_types_but_no_row_values(make_project, connector):
    with _Endpoint() as endpoint:
        endpoint.reply = '{"descriptions": {}}'
        project = make_project([])
        _drafts(project, connector, suggest_terms=True, llm=endpoint.config())
    sent = json.dumps(endpoint.requests)
    assert "customers" in sent and "VARCHAR" in sent.upper()
    # Row values from the database must never leave the process.
    assert "Ada" not in sent and "Grace" not in sent


def test_failed_model_falls_back_to_deterministic_descriptions(make_project, connector):
    with _Endpoint() as endpoint:
        endpoint.status = 500
        endpoint.reply = "{}"
        project = make_project([])
        drafts, result = _drafts(
            project, connector, suggest_terms=True, llm=endpoint.config()
        )
    cust = drafts["customers"]
    assert _column(cust, "name")["description"] == deterministic_description(
        "name", "VARCHAR"
    )
    assert _column(cust, "name")["properties"][DESCRIPTION_SOURCE] == "deterministic"
    assert any("model unavailable" in n and "customers" in n for n in result.notes)


def test_unusable_reply_falls_back_per_table(make_project, connector):
    with _Endpoint() as endpoint:
        endpoint.reply = '{"descriptions": "not an object"}'
        project = make_project([])
        drafts, _ = _drafts(
            project, connector, suggest_terms=True, llm=endpoint.config()
        )
    assert _column(drafts["orders"], "amount")["properties"][DESCRIPTION_SOURCE] == (
        "deterministic"
    )


def test_columns_the_model_leaves_out_are_filled_deterministically(
    make_project, connector
):
    with _Endpoint() as endpoint:
        endpoint.reply = json.dumps({"descriptions": {"id": "Customer key."}})
        project = make_project([])
        drafts, _ = _drafts(
            project, connector, suggest_terms=True, llm=endpoint.config()
        )
    cust = drafts["customers"]
    assert _column(cust, "id")["properties"][DESCRIPTION_SOURCE] == "llm"
    assert _column(cust, "name")["properties"][DESCRIPTION_SOURCE] == "deterministic"
    assert _column(cust, "name")["description"]  # never empty


def test_no_model_configured_uses_deterministic_and_says_so(make_project, connector):
    project = make_project([])
    drafts, result = _drafts(project, connector, suggest_terms=True, llm=None)
    assert any("no model configured" in n for n in result.notes)
    assert _column(drafts["customers"], "id")["properties"][DESCRIPTION_SOURCE] == (
        "deterministic"
    )


def test_descriptions_are_off_by_default(make_project, connector):
    project = make_project([])
    drafts, _ = _drafts(project, connector)
    column = _column(drafts["customers"], "id")
    assert "description" not in column
    assert DESCRIPTION_SOURCE not in column["properties"]
