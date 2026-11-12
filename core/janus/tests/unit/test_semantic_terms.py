"""Business terms and display names: rules, model refinement, and the draft file."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml
from typer.testing import CliRunner

from janus.context_cli import context_app
from janus.llm import LlmConfig
from janus.semantic_terms import (
    SOURCE_MODEL,
    SOURCE_RULE,
    build_terms,
    humanize_column,
    humanize_model,
    rule_terms,
    write_terms,
)
from tests.unit.conftest import model_dict

pytestmark = pytest.mark.unit


class _ChatServer:
    def __init__(self) -> None:
        self.status = 200
        self.reply: str | None = None
        self.requests: list[dict] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                server.requests.append(body)
                if server.status >= 300:
                    data = b'{"error": "down"}'
                else:
                    data = json.dumps(
                        {"choices": [{"message": {"content": server.reply}}]}
                    ).encode()
                self.send_response(server.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self._httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._httpd.server_port}/v1"
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._httpd.shutdown()
        self._httpd.server_close()

    def llm(self) -> LlmConfig:
        return LlmConfig(base_url=self.url, model="m", timeout=5)


@pytest.fixture
def server():
    with _ChatServer() as srv:
        yield srv


def _models():
    return [
        model_dict(
            "dim_order_items",
            "order_items",
            [("order_id", "INTEGER"), ("qty", "INTEGER"), ("cust_id", "INTEGER")],
            primary_key="order_id",
        ),
        model_dict(
            "customers",
            "customers",
            [("id", "INTEGER"), ("createdAt", "DATE")],
            primary_key="id",
        ),
    ]


# ── rules ───────────────────────────────────────────────────────────────────


def test_model_names_lose_prefixes_and_become_singular_terms():
    assert humanize_model("dim_order_items") == "Order Item"
    assert humanize_model("customers") == "Customer"
    assert humanize_model("fact_sales") == "Sale"


def test_column_names_expand_abbreviations_and_write_id_upper():
    assert humanize_column("cust_id") == "Customer ID"
    assert humanize_column("qty") == "Quantity"
    assert humanize_column("createdAt") == "Created At"
    assert humanize_column("amount") == "Amount"


def test_rule_terms_keep_the_raw_name_as_an_alias_when_it_differs():
    terms = {t.model: t for t in rule_terms(_models())}
    assert terms["dim_order_items"].term == "Order Item"
    assert "Dim Order Items" in terms["dim_order_items"].aliases
    assert terms["customers"].aliases == ["Customers"]
    assert {c.name: c.display_name for c in terms["dim_order_items"].columns} == {
        "order_id": "Order ID",
        "qty": "Quantity",
        "cust_id": "Customer ID",
    }


def test_rule_terms_are_marked_as_rules():
    terms = rule_terms(_models())
    assert all(t.source == SOURCE_RULE for t in terms)


# ── model refinement ────────────────────────────────────────────────────────


def test_model_refinement_replaces_terms_and_display_names(server):
    server.reply = json.dumps(
        {
            "tables": {
                "dim_order_items": {
                    "term": "Line Item",
                    "columns": {"qty": "Units Ordered", "unknown_col": "ignored"},
                },
                "not_a_model": {"term": "ignored"},
            }
        }
    )
    terms, notes = build_terms(_models(), llm=server.llm())
    item = next(t for t in terms if t.model == "dim_order_items")
    assert item.term == "Line Item"
    assert item.source == SOURCE_MODEL
    assert (
        next(c for c in item.columns if c.name == "qty").display_name == "Units Ordered"
    )
    assert notes == []
    assert "dim_order_items" in json.dumps(server.requests)


def test_failed_model_keeps_the_rule_terms(server):
    server.status = 500
    terms, notes = build_terms(_models(), llm=server.llm())
    assert all(t.source == SOURCE_RULE for t in terms)
    assert any("model unavailable" in n for n in notes)


def test_a_reply_without_tables_is_treated_as_a_failure(server):
    server.reply = json.dumps({"something": "else"})
    terms, notes = build_terms(_models(), llm=server.llm())
    assert all(t.source == SOURCE_RULE for t in terms)
    assert notes


def test_no_model_means_rules_only():
    terms, notes = build_terms(_models(), llm=None)
    assert all(t.source == SOURCE_RULE for t in terms)
    assert notes == []


# ── writing ─────────────────────────────────────────────────────────────────


def test_terms_are_written_under_draft_and_models_are_untouched(make_project):
    models = _models()
    project = make_project(models)
    before = (project / "models" / "customers" / "metadata.yml").read_text()
    terms, notes = build_terms(models, llm=None)
    path = write_terms(project, terms, notes)

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert {t["model"]: t["term"] for t in data["terms"]}[
        "dim_order_items"
    ] == "Order Item"
    assert (project / "models" / "customers" / "metadata.yml").read_text() == before


def test_cli_prints_terms_and_writes_the_draft(make_project):
    project = make_project(_models())
    result = CliRunner().invoke(context_app, ["terms", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert "dim_order_items  ->  Order Item" in result.output
    assert "cust_id  ->  Customer ID" in result.output
    assert (project / "draft" / "terms.yml").exists()


def test_cli_json_output(make_project):
    project = make_project(_models())
    result = CliRunner().invoke(
        context_app, ["terms", "--path", str(project), "--json"]
    )
    body = json.loads(result.output)
    by_model = {t["model"]: t["term"] for t in body["terms"]}
    assert by_model == {"customers": "Customer", "dim_order_items": "Order Item"}
