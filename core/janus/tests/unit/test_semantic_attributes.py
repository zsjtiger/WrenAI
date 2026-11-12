"""SQL attribute mining from the confirmed query history."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml
from typer.testing import CliRunner

from janus.context_cli import context_app
from janus.llm import LlmConfig
from janus.memory.markdown import write_query_markdown
from janus.semantic_attributes import (
    KIND_AGGREGATE,
    KIND_FILTER,
    STATUS_CONFIRMED,
    STATUS_REJECTED,
    STATUS_SUGGESTED,
    judge_with_model,
    mine_attributes,
    write_attributes,
)
from tests.unit.conftest import model_dict

pytestmark = pytest.mark.unit


def _models():
    return [
        model_dict(
            "orders",
            "orders",
            [
                ("order_id", "INTEGER"),
                ("amount", "DECIMAL(10,2)"),
                ("status", "VARCHAR"),
                ("cust_id", "INTEGER"),
            ],
            primary_key="order_id",
        ),
        model_dict(
            "customers",
            "customers",
            [("id", "INTEGER"), ("status", "VARCHAR"), ("region", "VARCHAR")],
            primary_key="id",
        ),
    ]


def _pair(sql: str, path: str) -> dict:
    return {"sql": sql, "path": path}


class _ChatServer:
    def __init__(self) -> None:
        self.status = 200
        self.reply: str | None = None
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers["Content-Length"]))
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


def _by_expression(result):
    return {a.expression: a for a in result.attributes}


# ── mining ──────────────────────────────────────────────────────────────────


def test_aggregates_and_filters_are_found_and_named():
    pairs = [
        _pair("SELECT SUM(amount) FROM orders WHERE status = 'shipped'", "a.md"),
        _pair(
            "SELECT SUM(amount), COUNT(*) FROM orders WHERE status = 'shipped'", "b.md"
        ),
    ]
    found = _by_expression(mine_attributes(pairs, _models(), "duckdb"))
    total = found["sum(amount)"]
    assert total.name == "total_amount"
    assert total.kind == KIND_AGGREGATE
    assert total.occurrences == 2
    shipped = found["status = 'shipped'"]
    assert shipped.name == "status_shipped"
    assert shipped.kind == KIND_FILTER
    assert "count(*)" not in found  # appears once, below the default threshold


def test_repeats_within_one_query_count_once():
    pairs = [
        _pair("SELECT SUM(amount), SUM(amount) FROM orders", "a.md"),
        _pair("SELECT 1 FROM orders", "b.md"),
    ]
    found = _by_expression(
        mine_attributes(pairs, _models(), "duckdb", min_occurrences=2)
    )
    assert "sum(amount)" not in found  # one query only, however often it repeats


def test_in_lists_and_distinct_counts_are_mined():
    pairs = [
        _pair(
            "SELECT COUNT(DISTINCT order_id) FROM orders WHERE status IN ('a','b')",
            "a.md",
        ),
        _pair(
            "SELECT COUNT(DISTINCT order_id) FROM orders WHERE status IN ('a','b')",
            "b.md",
        ),
    ]
    found = _by_expression(mine_attributes(pairs, _models(), "duckdb"))
    assert found["count(distinct order_id)"].name == "distinct_order_id_count"
    assert found["status in ('a', 'b')"].name == "status_in_list"


def test_a_column_shared_by_two_joined_models_is_query_level():
    pairs = [
        _pair(
            "SELECT SUM(o.amount) FROM orders o JOIN customers c ON o.cust_id = c.id "
            "WHERE c.status = 'vip'",
            "a.md",
        ),
        _pair(
            "SELECT SUM(o.amount) FROM orders o JOIN customers c ON o.cust_id = c.id "
            "WHERE c.status = 'vip'",
            "b.md",
        ),
    ]
    result = mine_attributes(pairs, _models(), "duckdb")
    vip = next(
        a
        for a in result.attributes
        if a.expression == "c.status = 'vip'" or a.expression == "status = 'vip'"
    )
    assert vip.model is None  # ``status`` exists in both models, so no single owner
    total = next(a for a in result.attributes if a.name == "total_amount")
    assert total.model == "orders"  # ``amount`` exists only in orders


def test_each_model_keeps_only_its_top_n_and_says_so():
    pairs = [
        _pair(f"SELECT SUM(amount) FROM orders WHERE status = 's{i}'", f"{i}a.md")
        for i in range(3)
    ] + [
        _pair(f"SELECT SUM(amount) FROM orders WHERE status = 's{i}'", f"{i}b.md")
        for i in range(3)
    ]
    result = mine_attributes(pairs, _models(), "duckdb", top_n=2)
    orders = [a for a in result.attributes if a.model == "orders"]
    assert len(orders) == 2
    assert any("lower-ranked" in n for n in result.notes)


def test_threshold_drops_rare_expressions():
    pairs = [_pair("SELECT SUM(amount) FROM orders", "a.md")]
    assert (
        mine_attributes(pairs, _models(), "duckdb", min_occurrences=2).attributes == []
    )
    assert mine_attributes(pairs, _models(), "duckdb", min_occurrences=1).attributes


def test_an_unparseable_query_is_noted_not_fatal():
    pairs = [
        _pair("SELECT FROM WHERE", "bad.md"),
        _pair("SELECT SUM(amount) FROM orders", "ok.md"),
    ]
    result = mine_attributes(pairs, _models(), "duckdb", min_occurrences=1)
    assert result.queries_scanned == 1
    assert any("bad.md" in n for n in result.notes)


# ── optional model judgement ────────────────────────────────────────────────


def _mined(server_reply: str | None = None):
    pairs = [
        _pair("SELECT SUM(amount) FROM orders WHERE status = 'shipped'", "a.md"),
        _pair("SELECT SUM(amount) FROM orders WHERE status = 'shipped'", "b.md"),
    ]
    return mine_attributes(pairs, _models(), "duckdb")


def test_model_can_confirm_and_rename(server):
    server.reply = json.dumps(
        {"attributes": {"sum(amount)": {"worth_naming": True, "name": "net_revenue"}}}
    )
    result = _mined()
    judge_with_model(result, server.llm())
    total = _by_expression(result)["sum(amount)"]
    assert total.status == STATUS_CONFIRMED
    assert total.name == "net_revenue"


def test_model_can_reject_and_invalid_names_are_ignored(server):
    server.reply = json.dumps(
        {
            "attributes": {
                "sum(amount)": {"worth_naming": True, "name": "Bad Name!"},
                "status = 'shipped'": {"worth_naming": False},
            }
        }
    )
    result = _mined()
    judge_with_model(result, server.llm())
    found = _by_expression(result)
    assert found["sum(amount)"].name == "total_amount"  # invalid rename ignored
    assert found["sum(amount)"].status == STATUS_CONFIRMED
    assert found["status = 'shipped'"].status == STATUS_REJECTED


def test_failed_model_keeps_the_rule_attributes(server):
    server.status = 500
    result = _mined()
    judge_with_model(result, server.llm())
    assert all(a.status == STATUS_SUGGESTED for a in result.attributes)
    assert any("model unavailable" in n for n in result.notes)


# ── writing and the CLI ─────────────────────────────────────────────────────


def test_write_puts_the_file_under_draft_and_leaves_models_alone(make_project):
    project = make_project(_models())
    before = (project / "models" / "orders" / "metadata.yml").read_text()
    result = _mined()
    path = write_attributes(project, result)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert {a["name"] for a in data["attributes"]} >= {"total_amount"}
    assert (project / "models" / "orders" / "metadata.yml").read_text() == before


def test_cli_mines_the_stored_queries(make_project):
    project = make_project(_models())
    write_query_markdown(
        project,
        "shipped revenue",
        "SELECT SUM(amount) FROM orders WHERE status = 'shipped'",
    )
    write_query_markdown(
        project,
        "shipped total",
        "SELECT SUM(amount) FROM orders WHERE status = 'shipped'",
    )
    result = CliRunner().invoke(
        context_app, ["attributes", "--path", str(project), "--min-occurrences", "2"]
    )
    assert result.exit_code == 0, result.output
    assert "orders.total_amount" in result.output
    assert "Scanned 2" in result.output
    assert (project / "draft" / "attributes.yml").exists()


def test_cli_json_output(make_project):
    project = make_project(_models())
    write_query_markdown(project, "a", "SELECT SUM(amount) FROM orders")
    write_query_markdown(project, "b", "SELECT SUM(amount) FROM orders")
    result = CliRunner().invoke(
        context_app, ["attributes", "--path", str(project), "--json"]
    )
    body = json.loads(result.output)
    assert body["attributes"][0]["expression"] == "sum(amount)"
