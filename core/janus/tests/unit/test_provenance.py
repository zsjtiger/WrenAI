"""Provenance and certification on query results, using a real engine and DuckDB."""

from __future__ import annotations

import pytest

from janus.context import validate_project
from janus.engine import JanusEngine
from janus.mcp_server import ServeContext, build_server
from janus.model.data_source import DataSource
from tests.unit.conftest import manifest_b64, model_dict, shop_connection_info

pytestmark = pytest.mark.unit


def _engine(project, shop_dir):
    return JanusEngine(
        manifest_b64(project),
        DataSource.duckdb,
        shop_connection_info(shop_dir),
        fallback=False,
    )


@pytest.fixture
def shop_project(make_project):
    """customers is certified, orders is not; the two are joined by a relationship."""
    customers = model_dict(
        "customers",
        "customers",
        [("id", "INTEGER"), ("name", "VARCHAR")],
        primary_key="id",
        properties={"certified": "true"},
    )
    orders = model_dict(
        "orders",
        "orders",
        [("order_id", "INTEGER"), ("cust_id", "INTEGER"), ("amount", "DECIMAL(10,2)")],
        primary_key="order_id",
    )
    rel = {
        "name": "orders_customers",
        "models": ["orders", "customers"],
        "join_type": "many_to_one",
        "condition": "orders.cust_id = customers.id",
    }
    return make_project([customers, orders], [rel])


def _ctx(project, engine):
    return ServeContext(
        project=project, engine=engine, allow_write=False, no_connect=False
    )


def _tool(project, engine, name):

    return build_server(_ctx(project, engine))._tool_manager._tools[name].fn


def test_engine_reports_models_used_and_their_certification(shop_project, shop_dir):
    with _engine(shop_project, shop_dir) as engine:
        table, models, sql = engine.query_with_provenance(
            'SELECT o.order_id, c.name FROM "orders" o '
            'JOIN "customers" c ON o.cust_id = c.id',
            10,
        )
    assert models == {"orders": False, "customers": True}
    assert table.num_rows == 2
    assert "SELECT" in sql.upper()


def test_run_sql_provenance_lists_models_and_warns_on_uncertified(
    shop_project, shop_dir
):
    with _engine(shop_project, shop_dir) as engine:
        run_sql = _tool(shop_project, engine, "run_sql")
        result = run_sql(sql='SELECT order_id FROM "orders"')

    assert result["provenance"]["models"] == ["orders"]
    assert result["provenance"]["certified"] == {"orders": False}
    assert result["warnings"] == ["model 'orders' is not certified"]
    assert "expanded_sql" not in result["provenance"]


def test_certified_only_query_has_no_warnings(shop_project, shop_dir):
    with _engine(shop_project, shop_dir) as engine:
        run_sql = _tool(shop_project, engine, "run_sql")
        result = run_sql(sql='SELECT name FROM "customers"')

    assert result["provenance"]["certified"] == {"customers": True}
    assert "warnings" not in result


def test_include_sql_returns_the_expanded_sql(shop_project, shop_dir):
    with _engine(shop_project, shop_dir) as engine:
        run_sql = _tool(shop_project, engine, "run_sql")
        result = run_sql(sql='SELECT name FROM "customers"', include_sql=True)

    assert "customers" in result["provenance"]["expanded_sql"].lower()


def test_knowledge_references_are_echoed_as_project_paths(shop_project, shop_dir):
    (shop_project / "knowledge" / "sql").mkdir(parents=True)
    (shop_project / "knowledge" / "sql" / "names.md").write_text("x", encoding="utf-8")
    with _engine(shop_project, shop_dir) as engine:
        run_sql = _tool(shop_project, engine, "run_sql")
        result = run_sql(sql='SELECT name FROM "customers"', knowledge=["sql/names.md"])
    assert result["provenance"]["knowledge"] == ["knowledge/sql/names.md"]


@pytest.mark.parametrize("ref", ["../janus_project.yml", "sql/missing.md"])
def test_knowledge_references_must_name_a_file_under_knowledge(
    shop_project, shop_dir, ref
):
    (shop_project / "knowledge").mkdir(exist_ok=True)
    with _engine(shop_project, shop_dir) as engine:
        run_sql = _tool(shop_project, engine, "run_sql")
        with pytest.raises(ValueError, match="does not name a file under knowledge"):
            run_sql(sql='SELECT name FROM "customers"', knowledge=[ref])


def test_list_and_describe_report_certification(shop_project, shop_dir):
    with _engine(shop_project, shop_dir) as engine:
        listed = _tool(shop_project, engine, "list_models")()
        described = _tool(shop_project, engine, "describe_model")("customers")
    by_name = {m["name"]: m["certified"] for m in listed["models"]}
    assert by_name == {"customers": True, "orders": False}
    assert described["certified"] is True


def test_validate_rejects_a_non_boolean_certification_value(make_project):
    project = make_project(
        [
            model_dict(
                "orders",
                "orders",
                [("order_id", "INTEGER")],
                properties={"certified": "yes please"},
            )
        ]
    )
    errors = [e for e in validate_project(project) if e.level == "error"]
    assert any(
        'properties.certified must be "true" or "false"' in e.message for e in errors
    )


def test_validate_accepts_true_false_and_yaml_booleans(make_project):
    project = make_project(
        [
            model_dict(
                "a", "a", [("id", "INTEGER")], properties={"certified": "false"}
            ),
            model_dict("b", "b", [("id", "INTEGER")], properties={"certified": True}),
        ]
    )
    errors = [e for e in validate_project(project) if e.level == "error"]
    assert errors == []
