"""Drift detection against a real DuckDB database (no connector mocks)."""

from __future__ import annotations

import pytest

from janus.connector.factory import get_connector
from janus.context_diff import diff_models, render_text
from janus.model.data_source import DataSource
from tests.unit.conftest import model_dict, shop_connection_info

pytestmark = pytest.mark.unit


@pytest.fixture
def connector(shop_dir):
    info = DataSource.duckdb.get_connection_info(shop_connection_info(shop_dir))
    conn = get_connector(DataSource.duckdb, info)
    yield conn
    conn.close()


def _in_sync_models():
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


def _kinds(report):
    return sorted((item.kind, item.model) for item in report.items)


def test_in_sync_project_reports_no_drift(connector):
    report = diff_models(_in_sync_models(), connector, DataSource.duckdb)
    assert report.has_drift is False
    assert sorted(report.checked) == ["customers", "orders"]
    assert "no drift" in render_text(report)


def test_column_in_yaml_but_not_database_is_reported(connector):
    models = _in_sync_models()
    models[0]["columns"].append(
        {"name": "email", "type": "VARCHAR", "is_calculated": False, "properties": {}}
    )
    report = diff_models(models, connector, DataSource.duckdb)
    assert _kinds(report) == [("column_missing", "customers")]
    assert "'email'" in report.items[0].detail


def test_column_in_database_but_not_yaml_is_reported(connector):
    models = _in_sync_models()
    models[1]["columns"] = [c for c in models[1]["columns"] if c["name"] != "amount"]
    report = diff_models(models, connector, DataSource.duckdb)
    assert _kinds(report) == [("column_extra", "orders")]


def test_type_change_is_reported(connector):
    models = _in_sync_models()
    models[1]["columns"][2]["type"] = "DOUBLE"
    report = diff_models(models, connector, DataSource.duckdb)
    assert _kinds(report) == [("type_mismatch", "orders")]


def test_primary_key_difference_is_reported(connector):
    models = _in_sync_models()
    models[0]["primary_key"] = "name"
    report = diff_models(models, connector, DataSource.duckdb)
    assert _kinds(report) == [("primary_key", "customers")]


def test_missing_table_is_reported(connector):
    models = _in_sync_models()
    models.append(model_dict("items", "items", [("id", "INTEGER")]))
    report = diff_models(models, connector, DataSource.duckdb)
    assert _kinds(report) == [("table_missing", "items")]


def test_table_without_a_model_is_reported(connector):
    models = _in_sync_models()[:1]  # drop orders from the YAML
    report = diff_models(models, connector, DataSource.duckdb)
    kinds = {item.kind for item in report.items}
    assert "table_unmodeled" in kinds
    assert any("orders" in item.detail for item in report.items)


def test_calculated_columns_and_ref_sql_models_are_not_compared(connector):
    models = _in_sync_models()
    models[0]["columns"].append(
        {
            "name": "label",
            "type": "VARCHAR",
            "is_calculated": True,
            "expression": "name || '!'",
            "properties": {},
        }
    )
    models.append({"name": "derived", "ref_sql": "SELECT 1", "columns": []})
    report = diff_models(models, connector, DataSource.duckdb)
    assert report.has_drift is False
    assert any("derived" in note for note in report.skipped)


def test_schema_filter_limits_the_checked_models(connector):
    report = diff_models(
        _in_sync_models(), connector, DataSource.duckdb, schema="other"
    )
    assert report.checked == []


def test_composite_primary_key_is_not_reported_as_drift(tmp_path):
    """MDL keys are single columns, so an unkeyed model over a composite key is not drift."""
    import duckdb  # noqa: PLC0415

    db_dir = tmp_path / "wh"
    db_dir.mkdir()
    conn = duckdb.connect(str(db_dir / "lines.duckdb"))
    conn.execute(
        "CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, "
        "quantity INTEGER, PRIMARY KEY (order_id, product_id))"
    )
    conn.close()
    info = DataSource.duckdb.get_connection_info(
        {"url": str(db_dir), "format": "duckdb"}
    )
    connector = get_connector(DataSource.duckdb, info)
    try:
        models = [
            model_dict(
                "order_items",
                "order_items",
                [
                    ("order_id", "INTEGER"),
                    ("product_id", "INTEGER"),
                    ("quantity", "INTEGER"),
                ],
                catalog="lines",
            )
        ]
        report = diff_models(models, connector, DataSource.duckdb)
    finally:
        connector.close()
    assert not any(item.kind == "primary_key" for item in report.items)
    assert report.has_drift is False
    assert any("composite primary key" in note for note in report.skipped)
