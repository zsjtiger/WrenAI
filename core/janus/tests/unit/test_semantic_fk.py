"""Undeclared foreign-key inference and bridge-table detection.

The embedding and model endpoints are real local HTTP servers, so the request
and fallback paths run as they would against a live service.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml
from typer.testing import CliRunner

from janus.context_cli import context_app
from janus.llm import LlmConfig
from janus.memory.api_embeddings import ApiEmbeddingConfig, ApiEmbeddings
from janus.model.data_source import DataSource
from janus.semantic_fk import (
    STATUS_AMBIGUOUS,
    STATUS_CONFIRMED,
    STATUS_REJECTED,
    STATUS_SUGGESTED,
    infer_foreign_keys,
    write_inference,
)
from tests.unit.conftest import model_dict

pytestmark = pytest.mark.unit


class _Server:
    """Serves /embeddings and /chat/completions with behavior set per test."""

    def __init__(self) -> None:
        self.embed = None  # callable(text) -> vector, or None to fail with 500
        self.chat_status = 200
        self.chat_reply: str | None = None  # content of the assistant message
        self.embed_requests: list[dict] = []
        self.chat_requests: list[dict] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - http.server API
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path.endswith("/embeddings"):
                    server.embed_requests.append(body)
                    if server.embed is None:
                        self._send(500, {"error": "down"})
                        return
                    items = [
                        {"index": i, "embedding": server.embed(t)}
                        for i, t in enumerate(body["input"])
                    ]
                    self._send(200, {"data": items})
                else:
                    server.chat_requests.append(body)
                    if server.chat_status >= 300:
                        self._send(server.chat_status, {"error": "down"})
                    else:
                        content = server.chat_reply
                        self._send(
                            200, {"choices": [{"message": {"content": content}}]}
                        )

            def _send(self, status, payload):
                data = json.dumps(payload).encode()
                self.send_response(status)
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

    def embedder(self) -> ApiEmbeddings:
        return ApiEmbeddings(
            ApiEmbeddingConfig(base_url=self.url, model="e", timeout=5)
        )


@pytest.fixture
def server():
    with _Server() as srv:
        yield srv


def _shop_models():
    return [
        model_dict(
            "customers",
            "customers",
            [("id", "INTEGER"), ("name", "VARCHAR")],
            primary_key="id",
        ),
        model_dict(
            "orders",
            "orders",
            [
                ("order_id", "INTEGER"),
                ("cust_id", "INTEGER"),
                ("amount", "DECIMAL(10,2)"),
            ],
            primary_key="order_id",
        ),
    ]


def _by_column(result, model, column):
    return next(
        s for s in result.suggestions if s.model == model and s.column == column
    )


# ── rules ───────────────────────────────────────────────────────────────────


def test_name_and_type_match_suggests_a_foreign_key():
    result = infer_foreign_keys(_shop_models(), [], DataSource.duckdb)
    s = _by_column(result, "orders", "cust_id")
    assert (s.target_model, s.target_column) == ("customers", "id")
    assert s.status == STATUS_SUGGESTED
    assert s.source == "rule"
    # ``cust`` is an abbreviation of ``customers``: a partial match, scored lower.
    assert s.score == 0.5
    assert "prefix" in s.reasons[0]


def test_exact_stem_scores_higher_than_a_prefix():
    models = [
        model_dict("customers", "customers", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "orders",
            "orders",
            [("order_id", "INTEGER"), ("customer_id", "INTEGER")],
            primary_key="order_id",
        ),
    ]
    s = _by_column(
        infer_foreign_keys(models, [], DataSource.duckdb), "orders", "customer_id"
    )
    assert s.score == 0.8
    assert "matches model" in s.reasons[0]


def test_incompatible_types_are_never_suggested():
    models = _shop_models()
    models[1]["columns"][1]["type"] = (
        "VARCHAR"  # cust_id as text, customers.id is integer
    )
    result = infer_foreign_keys(models, [], DataSource.duckdb)
    assert not any(s.column == "cust_id" for s in result.suggestions)


def test_declared_relationships_are_not_suggested_again():
    rel = {
        "name": "orders_customers",
        "models": ["orders", "customers"],
        "join_type": "many_to_one",
        "condition": "orders.cust_id = customers.id",
    }
    result = infer_foreign_keys(_shop_models(), [rel], DataSource.duckdb)
    assert not any(s.column == "cust_id" for s in result.suggestions)


def test_singular_and_plural_model_names_both_match():
    models = [
        model_dict(
            "products",
            "products",
            [("product_id", "INTEGER")],
            primary_key="product_id",
        ),
        model_dict(
            "order_lines",
            "order_lines",
            [("line_id", "INTEGER"), ("product_id", "INTEGER")],
            primary_key="line_id",
        ),
    ]
    result = infer_foreign_keys(models, [], DataSource.duckdb)
    s = _by_column(result, "order_lines", "product_id")
    assert s.target_model == "products"


def test_abbreviated_stem_is_a_partial_match():
    models = [
        model_dict("customers", "customers", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "orders",
            "orders",
            [("order_id", "INTEGER"), ("custid", "INTEGER")],
            primary_key="order_id",
        ),
    ]
    result = infer_foreign_keys(models, [], DataSource.duckdb)
    s = _by_column(result, "orders", "custid")
    assert s.score == 0.5
    assert s.status == STATUS_SUGGESTED


def test_tied_targets_are_ambiguous_without_an_embedder():
    models = [
        model_dict("owners", "owners", [("id", "INTEGER")], primary_key="id"),
        model_dict("owner", "owner", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "invoices",
            "invoices",
            [("invoice_id", "INTEGER"), ("owner_id", "INTEGER")],
            primary_key="invoice_id",
        ),
    ]
    result = infer_foreign_keys(models, [], DataSource.duckdb)
    s = _by_column(result, "invoices", "owner_id")
    assert s.status == STATUS_AMBIGUOUS
    assert set(s.alternatives) == {"owners", "owner"}


# ── embedding rerank ────────────────────────────────────────────────────────


def test_embedding_breaks_a_tie_when_it_clearly_prefers_one_target(server):
    server.embed = lambda text: (
        [1.0, 0.0] if text.startswith(("invoices", "owners")) else [0.0, 1.0]
    )
    models = [
        model_dict("owners", "owners", [("id", "INTEGER")], primary_key="id"),
        model_dict("owner", "owner", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "invoices",
            "invoices",
            [("invoice_id", "INTEGER"), ("owner_id", "INTEGER")],
            primary_key="invoice_id",
        ),
    ]
    result = infer_foreign_keys(
        models, [], DataSource.duckdb, embedder=server.embedder()
    )
    s = _by_column(result, "invoices", "owner_id")
    assert s.target_model == "owners"
    assert s.source == "embedding"
    assert s.status == STATUS_SUGGESTED


def test_unreachable_embedder_leaves_the_tie_ambiguous_with_a_note(server):
    server.embed = None  # the endpoint answers 500
    models = [
        model_dict("owners", "owners", [("id", "INTEGER")], primary_key="id"),
        model_dict("owner", "owner", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "invoices",
            "invoices",
            [("invoice_id", "INTEGER"), ("owner_id", "INTEGER")],
            primary_key="invoice_id",
        ),
    ]
    result = infer_foreign_keys(
        models, [], DataSource.duckdb, embedder=server.embedder()
    )
    assert _by_column(result, "invoices", "owner_id").status == STATUS_AMBIGUOUS
    assert any("embedding rerank unavailable" in n for n in result.notes)


# ── model confirmation ──────────────────────────────────────────────────────


def test_model_can_confirm_a_suggestion(server):
    server.chat_reply = json.dumps({"is_foreign_key": True, "reason": "customer key"})
    result = infer_foreign_keys(_shop_models(), [], DataSource.duckdb, llm=server.llm())
    s = _by_column(result, "orders", "cust_id")
    assert s.status == STATUS_CONFIRMED
    assert "model: customer key" in s.reasons
    sent = json.dumps(server.chat_requests)
    assert "cust_id" in sent and "customers" in sent


def test_model_can_reject_a_suggestion(server):
    server.chat_reply = json.dumps({"is_foreign_key": False, "reason": "unrelated"})
    result = infer_foreign_keys(_shop_models(), [], DataSource.duckdb, llm=server.llm())
    assert _by_column(result, "orders", "cust_id").status == STATUS_REJECTED


def test_failed_model_keeps_the_rule_result(server):
    server.chat_status = 500
    result = infer_foreign_keys(_shop_models(), [], DataSource.duckdb, llm=server.llm())
    assert _by_column(result, "orders", "cust_id").status == STATUS_SUGGESTED
    assert any("model unavailable" in n for n in result.notes)


# ── bridge tables ───────────────────────────────────────────────────────────


def _bridge_models(extra_attribute: bool = False):
    columns = [("order_id", "INTEGER"), ("product_id", "INTEGER")]
    if extra_attribute:
        columns.append(("quantity", "INTEGER"))
    return [
        model_dict(
            "orders", "orders", [("order_id", "INTEGER")], primary_key="order_id"
        ),
        model_dict(
            "products",
            "products",
            [("product_id", "INTEGER")],
            primary_key="product_id",
        ),
        # A bridge has a composite key, which MDL cannot express: no primary_key.
        model_dict("order_items", "order_items", columns),
    ]


def test_pure_key_table_is_a_bridge_with_a_join():
    result = infer_foreign_keys(_bridge_models(), [], DataSource.duckdb)
    assert len(result.bridges) == 1
    bridge = result.bridges[0]
    assert bridge.bridge == "order_items"
    assert bridge.attach_to == ("orders", "products")
    assert "JOIN order_items j ON j.order_id = a.order_id" in bridge.join_sql
    assert "JOIN products b ON j.product_id = b.product_id" in bridge.join_sql


def test_table_with_an_attribute_is_not_a_bridge():
    result = infer_foreign_keys(
        _bridge_models(extra_attribute=True), [], DataSource.duckdb
    )
    assert result.bridges == []


def test_bridge_uses_declared_relationships_too():
    models = _bridge_models()
    rels = [
        {
            "name": "a",
            "models": ["order_items", "orders"],
            "join_type": "many_to_one",
            "condition": "order_items.order_id = orders.order_id",
        },
        {
            "name": "b",
            "models": ["order_items", "products"],
            "join_type": "many_to_one",
            "condition": "order_items.product_id = products.product_id",
        },
    ]
    result = infer_foreign_keys(models, rels, DataSource.duckdb)
    assert [b.bridge for b in result.bridges] == ["order_items"]


# ── writing the draft ───────────────────────────────────────────────────────


def test_write_puts_everything_under_draft_and_leaves_models_alone(make_project):
    project = make_project(_shop_models())
    before = (project / "models" / "orders" / "metadata.yml").read_text()
    result = infer_foreign_keys(_shop_models(), [], DataSource.duckdb)
    summary = write_inference(project, result)

    rels = yaml.safe_load((project / "draft" / "relationships.yml").read_text())[
        "relationships"
    ]
    assert rels[0]["condition"] == "orders.cust_id = customers.id"
    assert summary["relationships_written"] == 1
    assert (project / "draft" / "fk_suggestions.yml").exists()
    assert (project / "models" / "orders" / "metadata.yml").read_text() == before

    # Running again does not duplicate the relationship.
    write_inference(project, result)
    rels = yaml.safe_load((project / "draft" / "relationships.yml").read_text())[
        "relationships"
    ]
    assert len(rels) == 1


def test_ambiguous_suggestions_write_no_relationship(make_project):
    models = [
        model_dict("owners", "owners", [("id", "INTEGER")], primary_key="id"),
        model_dict("owner", "owner", [("id", "INTEGER")], primary_key="id"),
        model_dict(
            "invoices",
            "invoices",
            [("invoice_id", "INTEGER"), ("owner_id", "INTEGER")],
            primary_key="invoice_id",
        ),
    ]
    project = make_project(models)
    write_inference(project, infer_foreign_keys(models, [], DataSource.duckdb))
    assert not (project / "draft" / "relationships.yml").exists()
    detail = yaml.safe_load((project / "draft" / "fk_suggestions.yml").read_text())
    assert detail["suggestions"][0]["status"] == STATUS_AMBIGUOUS


def test_cli_reports_suggestions_and_exits_zero(make_project):
    project = make_project(_shop_models())
    result = CliRunner().invoke(context_app, ["infer-fks", "--path", str(project)])
    assert result.exit_code == 0, result.output
    assert "orders.cust_id -> customers.id" in result.output
    assert (project / "draft" / "relationships.yml").exists()


def test_cli_json_output_is_machine_readable(make_project):
    project = make_project(_shop_models())
    result = CliRunner().invoke(
        context_app, ["infer-fks", "--path", str(project), "--json"]
    )
    body = json.loads(result.output)
    assert body["suggestions"][0]["column"] == "cust_id"
    assert body["summary"]["by_status"] == {STATUS_SUGGESTED: 1}


def test_cli_finds_foreign_keys_among_unpromoted_drafts(make_project):
    """Drafts are part of the project's context: infer-fks must see them too."""
    import yaml as _yaml  # noqa: PLC0415

    project = make_project([])
    for model in _shop_models():
        meta = project / "draft" / "models" / model["name"]
        meta.mkdir(parents=True)
        (meta / "metadata.yml").write_text(_yaml.safe_dump(model), encoding="utf-8")
    result = CliRunner().invoke(
        context_app, ["infer-fks", "--path", str(project), "--json"]
    )
    assert result.exit_code == 0, result.output
    body = json.loads(result.output)
    assert any(
        s["model"] == "orders" and s["column"] == "cust_id" for s in body["suggestions"]
    )


def test_warehouse_prefixes_do_not_block_a_match():
    """dim_store is referenced by store_key: the prefix is not part of the name."""
    models = [
        model_dict(
            "dim_store",
            "dim_store",
            [("store_key", "INTEGER")],
            primary_key="store_key",
        ),
        model_dict(
            "sales",
            "sales",
            [("sale_id", "INTEGER"), ("store_key", "INTEGER")],
            primary_key="sale_id",
        ),
    ]
    s = _by_column(
        infer_foreign_keys(models, [], DataSource.duckdb), "sales", "store_key"
    )
    assert (s.target_model, s.target_column) == ("dim_store", "store_key")
    assert s.status == STATUS_SUGGESTED


def test_a_models_own_primary_key_is_not_suggested_as_a_foreign_key():
    """companies.company_id is its own key; a same-named key in another table
    must not make it look like a reference."""
    models = [
        model_dict(
            "company", "company", [("company_id", "INTEGER")], primary_key="company_id"
        ),
        model_dict(
            "companies",
            "companies",
            [("company_id", "INTEGER")],
            primary_key="company_id",
        ),
    ]
    result = infer_foreign_keys(models, [], DataSource.duckdb)
    assert not any(
        s.model == "companies" and s.column == "company_id" for s in result.suggestions
    )
