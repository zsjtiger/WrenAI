"""PostgreSQL structure introspection (tables, columns, primary and foreign keys).

Runs against a real Postgres container, the same way test_postgres.py does.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

from janus.connector.factory import get_connector
from janus.connector.introspection import ColumnInfo, TableRef
from janus.context_diff import diff_models
from janus.model.data_source import DataSource

pytestmark = pytest.mark.postgres

_DDL = [
    "CREATE SCHEMA shop",
    "CREATE TABLE shop.customers (id integer PRIMARY KEY, "
    "name varchar(100) NOT NULL, created_at timestamptz)",
    "CREATE TABLE shop.orders (order_id integer, cust_id integer "
    "REFERENCES shop.customers(id), amount numeric(10,2), "
    "CONSTRAINT orders_pk PRIMARY KEY (order_id))",
    "CREATE TABLE shop.order_items (order_id integer, line integer, sku text, "
    "PRIMARY KEY (order_id, line), "
    "FOREIGN KEY (order_id) REFERENCES shop.orders(order_id))",
    "CREATE TABLE shop.nokey (a text, b text)",
]


@pytest.fixture(scope="module")
def pg_target():
    """Connection settings: a running server named by JANUS_TEST_PG_URL, or a container.

    With JANUS_TEST_PG_URL the schema must already exist (the tests only read).
    """
    url = os.environ.get("JANUS_TEST_PG_URL")
    if url:
        parsed = urlparse(url)
        yield {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/") or "postgres",
            "user": parsed.username,
            "password": parsed.password or "",
        }
        return
    with PostgresContainer("postgres:16-alpine") as container:
        with psycopg.connect(
            container.get_connection_url().replace("postgresql+psycopg2", "postgresql"),
            autocommit=True,
        ) as conn:
            for stmt in _DDL:
                conn.execute(stmt)
        yield {
            "host": container.get_container_host_ip(),
            "port": int(container.get_exposed_port(5432)),
            "database": container.dbname,
            "user": container.username,
            "password": container.password,
        }


@pytest.fixture(scope="module")
def connector(pg_target):
    info = DataSource.postgres.get_connection_info(pg_target)
    conn = get_connector(DataSource.postgres, info)
    yield conn
    conn.close()


def test_lists_tables_in_the_schema(connector):
    names = sorted(t.name for t in connector.list_tables("shop"))
    assert names == ["customers", "nokey", "order_items", "orders"]


def test_columns_carry_type_and_nullability(connector):
    columns = connector.list_columns(TableRef(name="customers", schema="shop"))
    assert columns == [
        ColumnInfo(name="id", data_type="integer", nullable=False),
        ColumnInfo(name="name", data_type="character varying", nullable=False),
        ColumnInfo(
            name="created_at", data_type="timestamp with time zone", nullable=True
        ),
    ]


def test_single_and_composite_primary_keys(connector):
    orders = connector.list_keys(TableRef(name="orders", schema="shop"))
    assert orders.primary_key == ("order_id",)
    items = connector.list_keys(TableRef(name="order_items", schema="shop"))
    assert items.primary_key == ("order_id", "line")  # key order preserved


def test_foreign_keys_point_at_the_referenced_table(connector):
    orders = connector.list_keys(TableRef(name="orders", schema="shop"))
    assert len(orders.foreign_keys) == 1
    fk = orders.foreign_keys[0]
    assert fk.columns == ("cust_id",)
    assert fk.ref_table.name == "customers"
    assert fk.ref_columns == ("id",)


def test_table_without_keys_reports_none(connector):
    keys = connector.list_keys(TableRef(name="nokey", schema="shop"))
    assert keys.primary_key == ()
    assert keys.foreign_keys == ()


def test_missing_table_has_no_columns(connector):
    assert connector.list_columns(TableRef(name="nope", schema="shop")) == []


def test_diff_detects_drift_against_postgres(connector):
    models = [
        {
            "name": "orders",
            "table_reference": {"schema": "shop", "table": "orders"},
            "primary_key": "order_id",
            "columns": [
                {"name": "order_id", "type": "INTEGER", "is_calculated": False},
                {"name": "amount", "type": "VARCHAR", "is_calculated": False},
            ],
        }
    ]
    report = diff_models(models, connector, DataSource.postgres)
    kinds = {item.kind for item in report.items}
    assert "type_mismatch" in kinds  # amount is numeric(10,2) in the database
    assert "column_extra" in kinds  # cust_id is in the database, not the YAML
