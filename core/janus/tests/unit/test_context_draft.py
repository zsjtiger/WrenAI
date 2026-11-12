"""Draft generation and promotion against a real DuckDB database."""

from __future__ import annotations

import pytest
import yaml

from janus.connector.factory import get_connector
from janus.context import load_models, validate_project
from janus.context_draft import apply_draft, generate_drafts, list_drafts
from janus.model.data_source import DataSource
from tests.unit.conftest import shop_connection_info

pytestmark = pytest.mark.unit


@pytest.fixture
def connector(shop_dir):
    info = DataSource.duckdb.get_connection_info(shop_connection_info(shop_dir))
    conn = get_connector(DataSource.duckdb, info)
    yield conn
    conn.close()


def _read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_generate_writes_only_under_draft(make_project, connector):
    project = make_project([])
    result = generate_drafts(project, connector, DataSource.duckdb)

    assert sorted(result.models) == ["customers", "orders"]
    assert list_drafts(project) == ["customers", "orders"]
    assert not any((project / "models").glob("*/metadata.yml"))

    orders = _read(project / "draft" / "models" / "orders" / "metadata.yml")
    assert orders["properties"] == {"draft": "true"}
    assert orders["primary_key"] == "order_id"
    assert orders["table_reference"]["table"] == "orders"
    types = {c["name"]: c["type"] for c in orders["columns"]}
    assert types["amount"] == "DECIMAL(10, 2)"


def test_generate_drafts_a_relationship_for_each_foreign_key(make_project, connector):
    project = make_project([])
    result = generate_drafts(project, connector, DataSource.duckdb)

    assert result.relationships == ["orders_customers_cust_id"]
    rels = _read(project / "draft" / "relationships.yml")["relationships"]
    assert rels[0]["models"] == ["orders", "customers"]
    assert rels[0]["condition"] == "orders.cust_id = customers.id"


def test_generate_skips_tables_already_modeled(make_project, connector, shop_dir):
    from tests.unit.conftest import model_dict  # noqa: PLC0415

    existing = model_dict(
        "customers",
        "customers",
        [("id", "INTEGER"), ("name", "VARCHAR")],
        primary_key="id",
    )
    project = make_project([existing])
    result = generate_drafts(project, connector, DataSource.duckdb)

    assert result.models == ["orders"]
    assert any("customers" in note for note in result.skipped)


def test_apply_promotes_model_and_relationship(make_project, connector):
    project = make_project([])
    generate_drafts(project, connector, DataSource.duckdb)

    added = apply_draft(project, "customers")
    assert added == []  # customers has no outgoing foreign key

    apply_draft(project, "orders")
    assert not (project / "draft" / "models" / "orders").exists()
    promoted = _read(project / "models" / "orders" / "metadata.yml")
    assert "draft" not in promoted["properties"]

    rels = _read(project / "relationships.yml")["relationships"]
    assert [r["name"] for r in rels] == ["orders_customers_cust_id"]
    errors = [e for e in validate_project(project) if e.level == "error"]
    assert errors == []
    assert {m["name"] for m in load_models(project)} == {"customers", "orders"}


def test_apply_refuses_a_missing_draft(make_project):
    project = make_project([])
    with pytest.raises(ValueError, match="no draft model named 'ghost'"):
        apply_draft(project, "ghost")


def test_failed_validation_rolls_the_promotion_back(make_project, connector):
    project = make_project([])
    generate_drafts(project, connector, DataSource.duckdb)
    # Make the draft invalid: a non-boolean certification value fails validation.
    meta = project / "draft" / "models" / "customers" / "metadata.yml"
    data = _read(meta)
    data["properties"]["certified"] = "maybe"
    meta.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="validation failed"):
        apply_draft(project, "customers")
    assert (project / "draft" / "models" / "customers" / "metadata.yml").exists()
    assert not (project / "models" / "customers").exists()
