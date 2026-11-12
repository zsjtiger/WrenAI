"""Shared fixtures for context-layer tests: a real DuckDB database and projects.

Nothing here mocks a connector. The database is an actual DuckDB file, and the
projects are written to disk so the code under test reads them the way a user's
project would be read.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest
import yaml

SHOP_TABLES = {
    "customers": (
        "CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL)"
    ),
    "orders": (
        "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, "
        "cust_id INTEGER REFERENCES customers(id), amount DECIMAL(10,2))"
    ),
}


@pytest.fixture
def shop_dir(tmp_path: Path) -> Path:
    """A directory holding ``shop.duckdb`` with customers and orders tables."""
    directory = tmp_path / "warehouse"
    directory.mkdir()
    conn = duckdb.connect(str(directory / "shop.duckdb"))
    for ddl in SHOP_TABLES.values():
        conn.execute(ddl)
    conn.execute("INSERT INTO customers VALUES (1, 'Ada'), (2, 'Grace')")
    conn.execute("INSERT INTO orders VALUES (10, 1, 9.5), (11, 2, 20.0)")
    conn.close()
    return directory


def shop_connection_info(directory: Path) -> dict[str, Any]:
    return {"url": str(directory), "format": "duckdb"}


def model_dict(
    name: str,
    table: str,
    columns: list[tuple[str, str]],
    *,
    primary_key: str | None = None,
    catalog: str = "shop",
    schema: str = "main",
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A model as it appears in ``models/<name>/metadata.yml``."""
    model: dict[str, Any] = {
        "name": name,
        "table_reference": {"catalog": catalog, "schema": schema, "table": table},
        "columns": [
            {"name": col, "type": typ, "is_calculated": False, "properties": {}}
            for col, typ in columns
        ],
        "cached": False,
        "properties": dict(properties or {}),
    }
    if primary_key:
        model["primary_key"] = primary_key
        for col in model["columns"]:
            if col["name"] == primary_key:
                col["is_primary_key"] = True
    return model


@pytest.fixture
def make_project(tmp_path: Path):
    """Write a janus project: ``make_project(models, relationships=None)``."""

    def _make(
        models: list[dict[str, Any]],
        relationships: list[dict[str, Any]] | None = None,
        *,
        root: Path | None = None,
    ) -> Path:
        project = root or (tmp_path / "project")
        project.mkdir(parents=True, exist_ok=True)
        (project / "janus_project.yml").write_text(
            "schema_version: 5\n"
            "name: shop\n"
            'version: "1.0"\n'
            "catalog: janus\n"
            "schema: public\n"
            "data_source: duckdb\n",
            encoding="utf-8",
        )
        (project / "relationships.yml").write_text(
            yaml.safe_dump({"relationships": relationships or []}, sort_keys=False),
            encoding="utf-8",
        )
        for model in models:
            model_dir = project / "models" / model["name"]
            model_dir.mkdir(parents=True, exist_ok=True)
            (model_dir / "metadata.yml").write_text(
                yaml.safe_dump(model, sort_keys=False), encoding="utf-8"
            )
        return project

    return _make


def manifest_b64(project: Path) -> str:
    """The base64 MDL string the engine takes, built from the project's YAML."""
    from janus.context import build_json  # noqa: PLC0415

    return base64.b64encode(json.dumps(build_json(project)).encode()).decode()
