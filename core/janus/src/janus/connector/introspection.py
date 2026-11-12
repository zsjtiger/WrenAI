"""Catalog introspection shared by all connectors: tables, columns and keys.

Connectors do not implement introspection themselves. Each connector declares
an *introspection flavor* (``ConnectorABC.introspection_flavor``), set by the
factory from the ``DataSource``. The flavor picks the catalog SQL, and this
module normalizes the driver rows into the dataclasses below.

Flavors and what they can report:

* ``ansi``       information_schema: tables, columns, primary and foreign keys
* ``ansi_pk``    information_schema: tables, columns, primary keys (no FKs)
* ``nokeys``     information_schema: tables and columns only
* ``mysql``      information_schema with MySQL key metadata
* ``duckdb``     duckdb_tables()/duckdb_columns()/duckdb_constraints()
* ``clickhouse`` system.tables/system.columns (primary keys, no FKs)
* ``oracle``     all_tables/all_tab_columns/all_constraints
* ``bigquery``   per-dataset INFORMATION_SCHEMA (primary keys, no FKs)
* ``spark``      SHOW TABLES / DESCRIBE TABLE (no keys, nullability unknown)

A flavor that cannot report keys returns ``primary_key_supported=False`` in
``KeyInfo``; callers must not treat an empty key as "no primary key" then.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from janus.model.error import ErrorCode, JanusError

#: Schemas that hold catalog metadata rather than user tables.
SYSTEM_SCHEMAS = frozenset(
    {
        "information_schema",
        "pg_catalog",
        "pg_toast",
        "mysql",
        "performance_schema",
        "sys",
        "system",
    }
)


@dataclass(frozen=True)
class TableRef:
    name: str
    schema: str | None = None
    catalog: str | None = None


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool


@dataclass(frozen=True)
class ForeignKey:
    name: str
    columns: tuple[str, ...]
    ref_table: TableRef
    ref_columns: tuple[str, ...]


@dataclass(frozen=True)
class KeyInfo:
    primary_key: tuple[str, ...] = ()
    foreign_keys: tuple[ForeignKey, ...] = ()
    primary_key_supported: bool = True
    foreign_keys_supported: bool = True


def lit(value: str) -> str:
    """SQL string literal with single quotes doubled."""
    return "'" + value.replace("'", "''") + "'"


def _require_schema(table: TableRef) -> str:
    if not table.schema:
        raise ValueError(f"table '{table.name}' needs a schema to read its structure")
    return table.schema


def _is_nullable(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().upper() in ("YES", "Y", "TRUE", "T", "1")


def _lower_keys(row: dict) -> dict:
    return {str(k).lower(): v for k, v in row.items()}


class _Flavor:
    """Base flavor. Subclasses supply SQL; this class supplies the logic."""

    primary_key_supported = True
    foreign_keys_supported = True

    def __init__(self, run: Callable[[str], list[dict]]) -> None:
        self._run = run

    # --- SQL hooks -------------------------------------------------------
    def tables_sql(self, schema: str | None) -> str:
        """Rows with ``table_schema`` and ``table_name`` (optionally catalog)."""
        raise NotImplementedError

    def columns_sql(self, table: TableRef) -> str:
        """Rows with ``column_name``, ``data_type`` and ``is_nullable``."""
        raise NotImplementedError

    def primary_key_sql(self, table: TableRef) -> str:
        """Rows with ``column_name`` in key order."""
        raise NotImplementedError

    def foreign_key_sql(self, table: TableRef) -> str:
        """Rows: ``constraint_name, column_name, ref_schema, ref_table,
        ref_column`` in constraint then key order."""
        raise NotImplementedError

    # --- public surface --------------------------------------------------
    def list_tables(self, schema: str | None) -> list[TableRef]:
        refs = []
        for row in self._run(self.tables_sql(schema)):
            table_schema = row.get("table_schema")
            if table_schema is not None and str(table_schema).lower() in (
                SYSTEM_SCHEMAS
            ):
                continue
            refs.append(
                TableRef(
                    name=str(row["table_name"]),
                    schema=None if table_schema is None else str(table_schema),
                    catalog=row.get("table_catalog"),
                )
            )
        return refs

    def list_columns(self, table: TableRef) -> list[ColumnInfo]:
        return [
            ColumnInfo(
                name=str(row["column_name"]),
                data_type=str(row["data_type"]),
                nullable=_is_nullable(row.get("is_nullable")),
            )
            for row in self._run(self.columns_sql(table))
        ]

    def list_keys(self, table: TableRef) -> KeyInfo:
        pk: tuple[str, ...] = ()
        if self.primary_key_supported:
            pk = tuple(
                str(r["column_name"]) for r in self._run(self.primary_key_sql(table))
            )
        fks: tuple[ForeignKey, ...] = ()
        if self.foreign_keys_supported:
            fks = _group_foreign_keys(self._run(self.foreign_key_sql(table)))
        return KeyInfo(
            primary_key=pk,
            foreign_keys=fks,
            primary_key_supported=self.primary_key_supported,
            foreign_keys_supported=self.foreign_keys_supported,
        )


def _group_foreign_keys(rows: list[dict]) -> tuple[ForeignKey, ...]:
    grouped: dict[str, dict] = {}
    for row in rows:
        entry = grouped.setdefault(
            str(row["constraint_name"]),
            {"columns": [], "ref_columns": [], "ref": None},
        )
        entry["columns"].append(str(row["column_name"]))
        entry["ref_columns"].append(str(row["ref_column"]))
        entry["ref"] = TableRef(
            name=str(row["ref_table"]),
            schema=None if row.get("ref_schema") is None else str(row["ref_schema"]),
        )
    return tuple(
        ForeignKey(
            name=name,
            columns=tuple(e["columns"]),
            ref_table=e["ref"],
            ref_columns=tuple(e["ref_columns"]),
        )
        for name, e in grouped.items()
    )


class _AnsiFlavor(_Flavor):
    def __init__(self, run, *, primary_key: bool, foreign_keys: bool) -> None:
        super().__init__(run)
        self.primary_key_supported = primary_key
        self.foreign_keys_supported = foreign_keys

    def tables_sql(self, schema):
        where = "table_type IN ('BASE TABLE', 'TABLE')"
        if schema:
            where += f" AND table_schema = {lit(schema)}"
        return (
            "SELECT table_catalog, table_schema, table_name "
            f"FROM information_schema.tables WHERE {where}"
        )

    def columns_sql(self, table):
        return (
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            f"WHERE table_schema = {lit(_require_schema(table))} "
            f"AND table_name = {lit(table.name)} ORDER BY ordinal_position"
        )

    def primary_key_sql(self, table):
        return (
            "SELECT kcu.column_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "AND tc.table_schema = kcu.table_schema "
            "AND tc.table_name = kcu.table_name "
            "WHERE tc.constraint_type = 'PRIMARY KEY' "
            f"AND tc.table_schema = {lit(_require_schema(table))} "
            f"AND tc.table_name = {lit(table.name)} "
            "ORDER BY kcu.ordinal_position"
        )

    def foreign_key_sql(self, table):
        return (
            "SELECT kcu.constraint_name, kcu.column_name, "
            "ccu.table_schema AS ref_schema, ccu.table_name AS ref_table, "
            "ccu.column_name AS ref_column "
            "FROM information_schema.referential_constraints rc "
            "JOIN information_schema.key_column_usage kcu "
            "ON kcu.constraint_name = rc.constraint_name "
            "AND kcu.constraint_schema = rc.constraint_schema "
            "JOIN information_schema.constraint_column_usage ccu "
            "ON ccu.constraint_name = rc.unique_constraint_name "
            "AND ccu.constraint_schema = rc.unique_constraint_schema "
            f"WHERE kcu.table_schema = {lit(_require_schema(table))} "
            f"AND kcu.table_name = {lit(table.name)} "
            "ORDER BY kcu.constraint_name, kcu.ordinal_position"
        )


class _MySqlFlavor(_Flavor):
    def tables_sql(self, schema):
        scope = lit(schema) if schema else "DATABASE()"
        return (
            "SELECT table_schema, table_name FROM information_schema.tables "
            f"WHERE table_type = 'BASE TABLE' AND table_schema = {scope}"
        )

    def columns_sql(self, table):
        return (
            "SELECT column_name, data_type, is_nullable "
            "FROM information_schema.columns "
            f"WHERE table_schema = {lit(_require_schema(table))} "
            f"AND table_name = {lit(table.name)} ORDER BY ordinal_position"
        )

    def primary_key_sql(self, table):
        return (
            "SELECT column_name FROM information_schema.key_column_usage "
            "WHERE constraint_name = 'PRIMARY' "
            f"AND table_schema = {lit(_require_schema(table))} "
            f"AND table_name = {lit(table.name)} ORDER BY ordinal_position"
        )

    def foreign_key_sql(self, table):
        return (
            "SELECT constraint_name, column_name, "
            "referenced_table_schema AS ref_schema, "
            "referenced_table_name AS ref_table, "
            "referenced_column_name AS ref_column "
            "FROM information_schema.key_column_usage "
            "WHERE referenced_table_name IS NOT NULL "
            f"AND table_schema = {lit(_require_schema(table))} "
            f"AND table_name = {lit(table.name)} "
            "ORDER BY constraint_name, ordinal_position"
        )


class _DuckDbFlavor(_Flavor):
    def tables_sql(self, schema):
        where = "database_name <> 'system' AND database_name <> 'temp'"
        if schema:
            where += f" AND schema_name = {lit(schema)}"
        return (
            "SELECT database_name AS table_catalog, schema_name AS table_schema, "
            f"table_name FROM duckdb_tables() WHERE {where}"
        )

    def _scope(self, table: TableRef) -> str:
        scope = (
            f"schema_name = {lit(_require_schema(table))} "
            f"AND table_name = {lit(table.name)}"
        )
        if table.catalog:
            scope += f" AND database_name = {lit(table.catalog)}"
        return scope

    def columns_sql(self, table):
        return (
            "SELECT column_name, data_type, is_nullable FROM duckdb_columns() "
            f"WHERE {self._scope(table)} ORDER BY column_index"
        )

    def primary_key_sql(self, table):
        return (
            "SELECT unnest(constraint_column_names) AS column_name "
            "FROM duckdb_constraints() "
            f"WHERE constraint_type = 'PRIMARY KEY' AND {self._scope(table)}"
        )

    def foreign_key_sql(self, table):
        return (
            "SELECT constraint_name, "
            "unnest(constraint_column_names) AS column_name, "
            # duckdb_constraints() does not report the referenced schema; a
            # foreign key is assumed to point into the same schema.
            "schema_name AS ref_schema, referenced_table AS ref_table, "
            "unnest(referenced_column_names) AS ref_column "
            "FROM duckdb_constraints() "
            f"WHERE constraint_type = 'FOREIGN KEY' AND {self._scope(table)}"
        )


class _ClickHouseFlavor(_Flavor):
    foreign_keys_supported = False

    def tables_sql(self, schema):
        where = "engine NOT LIKE '%View%'"
        if schema:
            where += f" AND database = {lit(schema)}"
        return (
            "SELECT database AS table_schema, name AS table_name "
            f"FROM system.tables WHERE {where}"
        )

    def columns_sql(self, table):
        return (
            "SELECT name AS column_name, type AS data_type, "
            "startsWith(type, 'Nullable(') AS is_nullable "
            "FROM system.columns "
            f"WHERE database = {lit(_require_schema(table))} "
            f"AND table = {lit(table.name)} ORDER BY position"
        )

    def primary_key_sql(self, table):
        return (
            "SELECT name AS column_name FROM system.columns "
            f"WHERE database = {lit(_require_schema(table))} "
            f"AND table = {lit(table.name)} AND is_in_primary_key = 1 "
            "ORDER BY position"
        )


class _OracleFlavor(_Flavor):
    _SYSTEM_OWNERS = frozenset(
        {
            "SYS",
            "SYSTEM",
            "XDB",
            "MDSYS",
            "CTXSYS",
            "OUTLN",
            "DBSNMP",
            "WMSYS",
            "APPQOSSYS",
            "ORDSYS",
            "ORDDATA",
            "OLAPSYS",
            "DVSYS",
            "AUDSYS",
            "LBACSYS",
            "OJVMSYS",
            "DBSFWUSER",
            "SYSMAN",
        }
    )

    def list_tables(self, schema):
        # Oracle has no implicit "all schemas" default; without a schema the
        # current user's tables are listed, matching what the account can use.
        scope = lit(schema.upper()) if schema else "USER"
        rows = self._run(
            "SELECT owner AS table_schema, table_name FROM all_tables "
            f"WHERE owner = {scope}"
        )
        return [
            TableRef(name=str(r["table_name"]), schema=str(r["table_schema"]))
            for r in rows
            if str(r["table_schema"]).upper() not in self._SYSTEM_OWNERS
        ]

    def columns_sql(self, table):
        return (
            "SELECT column_name, data_type, nullable AS is_nullable "
            "FROM all_tab_columns "
            f"WHERE owner = {lit(_require_schema(table).upper())} "
            f"AND table_name = {lit(table.name)} ORDER BY column_id"
        )

    def primary_key_sql(self, table):
        return (
            "SELECT cc.column_name FROM all_constraints c "
            "JOIN all_cons_columns cc "
            "ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name "
            "WHERE c.constraint_type = 'P' "
            f"AND c.owner = {lit(_require_schema(table).upper())} "
            f"AND c.table_name = {lit(table.name)} ORDER BY cc.position"
        )

    def foreign_key_sql(self, table):
        return (
            "SELECT c.constraint_name, cc.column_name, "
            "rc.owner AS ref_schema, rc.table_name AS ref_table, "
            "rcc.column_name AS ref_column "
            "FROM all_constraints c "
            "JOIN all_cons_columns cc "
            "ON c.owner = cc.owner AND c.constraint_name = cc.constraint_name "
            "JOIN all_constraints rc "
            "ON c.r_owner = rc.owner AND c.r_constraint_name = rc.constraint_name "
            "JOIN all_cons_columns rcc "
            "ON rc.owner = rcc.owner AND rc.constraint_name = rcc.constraint_name "
            "AND rcc.position = cc.position "
            "WHERE c.constraint_type = 'R' "
            f"AND c.owner = {lit(_require_schema(table).upper())} "
            f"AND c.table_name = {lit(table.name)} "
            "ORDER BY c.constraint_name, cc.position"
        )


class _BigQueryFlavor(_Flavor):
    foreign_keys_supported = False

    @staticmethod
    def _dataset(schema: str | None) -> str:
        if not schema:
            raise ValueError(
                "BigQuery introspection needs a dataset (schema) name; "
                "INFORMATION_SCHEMA is per dataset"
            )
        return "`" + schema.replace("`", "") + "`"

    def list_tables(self, schema):
        dataset = self._dataset(schema)
        rows = self._run(
            "SELECT table_schema, table_name "
            f"FROM {dataset}.INFORMATION_SCHEMA.TABLES "
            "WHERE table_type = 'BASE TABLE'"
        )
        return [TableRef(name=str(r["table_name"]), schema=schema) for r in rows]

    def columns_sql(self, table):
        return (
            "SELECT column_name, data_type, is_nullable "
            f"FROM {self._dataset(_require_schema(table))}.INFORMATION_SCHEMA.COLUMNS "
            f"WHERE table_name = {lit(table.name)} ORDER BY ordinal_position"
        )

    def primary_key_sql(self, table):
        ds = self._dataset(_require_schema(table))
        return (
            "SELECT kcu.column_name "
            f"FROM {ds}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            f"JOIN {ds}.INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "WHERE tc.constraint_type = 'PRIMARY KEY' "
            f"AND tc.table_name = {lit(table.name)} "
            f"AND kcu.table_name = {lit(table.name)} "
            "ORDER BY kcu.ordinal_position"
        )


class _SparkFlavor(_Flavor):
    primary_key_supported = False
    foreign_keys_supported = False

    @staticmethod
    def _ident(*parts: str) -> str:
        return ".".join("`" + p.replace("`", "") + "`" for p in parts)

    def list_tables(self, schema):
        sql = f"SHOW TABLES IN {self._ident(schema)}" if schema else "SHOW TABLES"
        rows = self._run(sql)
        return [
            TableRef(
                name=str(r["tablename"]),
                schema=str(r["namespace"]) if r.get("namespace") else schema,
            )
            for r in rows
            if not _is_truthy(r.get("istemporary"))
        ]

    def list_columns(self, table):
        parts = [_require_schema(table), table.name]
        rows = self._run(f"DESCRIBE TABLE {self._ident(*parts)}")
        columns = []
        for row in rows:
            name = row.get("col_name")
            if not name or str(name).startswith("#"):
                break
            columns.append(
                ColumnInfo(
                    name=str(name),
                    data_type=str(row.get("data_type") or ""),
                    # DESCRIBE does not report nullability; report it as nullable.
                    nullable=True,
                )
            )
        return columns


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "t", "yes")


def _build_flavor(name: str, run: Callable[[str], list[dict]]) -> _Flavor:
    if name == "ansi":
        return _AnsiFlavor(run, primary_key=True, foreign_keys=True)
    if name == "ansi_pk":
        return _AnsiFlavor(run, primary_key=True, foreign_keys=False)
    if name == "nokeys":
        return _AnsiFlavor(run, primary_key=False, foreign_keys=False)
    if name == "mysql":
        return _MySqlFlavor(run)
    if name == "duckdb":
        return _DuckDbFlavor(run)
    if name == "clickhouse":
        return _ClickHouseFlavor(run)
    if name == "oracle":
        return _OracleFlavor(run)
    if name == "bigquery":
        return _BigQueryFlavor(run)
    if name == "spark":
        return _SparkFlavor(run)
    raise JanusError(
        ErrorCode.NOT_IMPLEMENTED, f"Unknown introspection flavor '{name}'"
    )


def _runner(connector) -> Callable[[str], list[dict]]:
    def run(sql: str) -> list[dict]:
        return [_lower_keys(row) for row in connector.query(sql, None).to_pylist()]

    return run


def list_tables(connector, schema: str | None = None) -> list[TableRef]:
    flavor = _build_flavor(connector.introspection_flavor, _runner(connector))
    return flavor.list_tables(schema)


def list_columns(connector, table: TableRef) -> list[ColumnInfo]:
    flavor = _build_flavor(connector.introspection_flavor, _runner(connector))
    return flavor.list_columns(table)


def list_keys(connector, table: TableRef) -> KeyInfo:
    flavor = _build_flavor(connector.introspection_flavor, _runner(connector))
    return flavor.list_keys(table)
