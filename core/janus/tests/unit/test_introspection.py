"""Catalog introspection: real DuckDB reads, plus flavor coverage for every source."""

from __future__ import annotations

import pytest

from janus.connector.factory import _INTROSPECTION_FLAVOR, get_connector
from janus.connector.introspection import (
    ColumnInfo,
    TableRef,
    _AnsiFlavor,
    _build_flavor,
)
from janus.model.data_source import DataSource
from tests.unit.conftest import shop_connection_info

pytestmark = pytest.mark.unit


@pytest.fixture
def shop(shop_dir):
    info = DataSource.duckdb.get_connection_info(shop_connection_info(shop_dir))
    connector = get_connector(DataSource.duckdb, info)
    yield connector
    connector.close()


def test_duckdb_lists_user_tables(shop):
    names = {(t.catalog, t.schema, t.name) for t in shop.list_tables()}
    assert names == {("shop", "main", "customers"), ("shop", "main", "orders")}


def test_duckdb_columns_report_types_and_nullability(shop):
    columns = shop.list_columns(
        TableRef(name="customers", schema="main", catalog="shop")
    )
    assert columns == [
        ColumnInfo(name="id", data_type="INTEGER", nullable=False),
        ColumnInfo(name="name", data_type="VARCHAR", nullable=False),
    ]


def test_duckdb_primary_and_foreign_keys(shop):
    keys = shop.list_keys(TableRef(name="orders", schema="main", catalog="shop"))
    assert keys.primary_key == ("order_id",)
    assert keys.primary_key_supported and keys.foreign_keys_supported
    assert len(keys.foreign_keys) == 1
    fk = keys.foreign_keys[0]
    assert fk.columns == ("cust_id",)
    assert fk.ref_table.name == "customers"
    assert fk.ref_columns == ("id",)


def test_missing_table_has_no_columns(shop):
    # Drift detection relies on this: an absent table reads as "no columns".
    assert shop.list_columns(TableRef(name="nope", schema="main", catalog="shop")) == []


def test_every_data_source_declares_a_known_flavor():
    # A new DataSource without a flavor would silently fall back to "ansi".
    missing = [ds.value for ds in DataSource if ds not in _INTROSPECTION_FLAVOR]
    assert missing == []
    for name in set(_INTROSPECTION_FLAVOR.values()):
        _build_flavor(name, lambda sql: [])  # raises for an unknown flavor


def test_nokeys_flavor_reports_keys_unsupported_without_querying():
    def run(sql):
        raise AssertionError(f"no key query should run, got: {sql}")

    keys = _build_flavor("nokeys", run).list_keys(TableRef(name="t", schema="s"))
    assert keys.primary_key_supported is False
    assert keys.foreign_keys_supported is False


def test_identifiers_are_escaped_in_catalog_sql():
    captured: list[str] = []

    def run(sql):
        captured.append(sql)
        return []

    flavor = _AnsiFlavor(run, primary_key=True, foreign_keys=True)
    flavor.list_columns(TableRef(name="o'brien", schema="it's"))
    assert "'it''s'" in captured[0]
    assert "'o''brien'" in captured[0]
