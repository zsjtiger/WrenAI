"""Drift detection: compare a context project's YAML with a live database.

``diff_project`` reads each model's ``table_reference`` through a connector and
reports where the YAML and the database disagree:

* ``table_missing``    model points at a table the database does not have
* ``column_missing``   column in YAML, not in the database
* ``column_extra``     column in the database, not in YAML
* ``type_mismatch``    column types differ after normalization
* ``primary_key``      primary key differs (skipped when the connector cannot
                       report keys)
* ``table_unmodeled``  table in the database that no model references

Calculated columns and ``ref_sql`` models are not compared against the
database: a calculated column has no physical column, and a ref_sql model has
no fixed table. Both are listed under ``skipped``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from janus.connector.introspection import TableRef
from janus.mdl.cte_rewriter import get_sqlglot_dialect
from janus.model.data_source import DataSource
from janus.type_mapping import parse_type


@dataclass(frozen=True)
class DriftItem:
    kind: str
    model: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class DriftReport:
    data_source: str
    items: list[DriftItem] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    primary_key_checked: bool = True

    @property
    def has_drift(self) -> bool:
        return bool(self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "data_source": self.data_source,
            "has_drift": self.has_drift,
            "primary_key_checked": self.primary_key_checked,
            "checked": self.checked,
            "skipped": self.skipped,
            "items": [item.to_dict() for item in self.items],
        }


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


def _is_compared_column(column: dict) -> bool:
    if column.get("is_calculated") or column.get("expression"):
        return False
    return bool(column.get("name"))


def _type_key(type_str: str | None, dialect: str) -> str | None:
    if not type_str:
        return None
    return parse_type(str(type_str), dialect).upper().replace(" ", "")


def _pk_set(value: Any) -> frozenset[str]:
    if not value:
        return frozenset()
    if isinstance(value, str):
        return frozenset({_norm(value)})
    return frozenset(_norm(str(v)) for v in value)


def diff_models(
    models: list[dict],
    connector: Any,
    data_source: DataSource,
    *,
    schema: str | None = None,
) -> DriftReport:
    """Compare ``models`` (as loaded from YAML) with ``connector``'s database."""
    dialect = get_sqlglot_dialect(data_source)
    report = DriftReport(data_source=data_source.value)
    modeled: set[tuple[str, str]] = set()

    for model in models:
        name = model.get("name", "?")
        tref = model.get("table_reference")
        if not tref and model.get("ref_sql"):
            report.skipped.append(f"{name}: ref_sql model (no fixed table)")
            continue
        if not tref or not tref.get("table"):
            report.skipped.append(f"{name}: no table_reference")
            continue

        table_schema = tref.get("schema") or None
        table = TableRef(
            name=str(tref["table"]),
            schema=table_schema,
            catalog=tref.get("catalog") or None,
        )
        modeled.add((_norm(table.schema), _norm(table.name)))
        if schema is not None and _norm(table_schema) != _norm(schema):
            continue

        report.checked.append(name)
        db_columns = connector.list_columns(table)
        if not db_columns:
            report.items.append(
                DriftItem(
                    "table_missing",
                    name,
                    f"table {_qualified(table)} does not exist in the database",
                )
            )
            continue

        yaml_columns = [c for c in model.get("columns") or [] if _is_compared_column(c)]
        db_by_name = {_norm(c.name): c for c in db_columns}
        yaml_names = {_norm(c["name"]) for c in yaml_columns}

        for column in yaml_columns:
            key = _norm(column["name"])
            if key not in db_by_name:
                report.items.append(
                    DriftItem(
                        "column_missing",
                        name,
                        f"column '{column['name']}' is in YAML but not in the database",
                    )
                )
                continue
            yaml_type = _type_key(column.get("type"), dialect)
            db_type = _type_key(db_by_name[key].data_type, dialect)
            if yaml_type and db_type and yaml_type != db_type:
                report.items.append(
                    DriftItem(
                        "type_mismatch",
                        name,
                        f"column '{column['name']}': YAML type {column.get('type')}"
                        f", database type {db_by_name[key].data_type}",
                    )
                )

        for db_column in db_columns:
            if _norm(db_column.name) not in yaml_names:
                report.items.append(
                    DriftItem(
                        "column_extra",
                        name,
                        f"column '{db_column.name}' is in the database but not in YAML",
                    )
                )

        keys = connector.list_keys(table)
        if keys.primary_key_supported:
            yaml_pk = _pk_set(model.get("primary_key"))
            db_pk = _pk_set(keys.primary_key)
            if yaml_pk != db_pk:
                report.items.append(
                    DriftItem(
                        "primary_key",
                        name,
                        "primary key differs: YAML "
                        f"{sorted(yaml_pk) or 'none'}, database "
                        f"{sorted(db_pk) or 'none'}",
                    )
                )
        else:
            report.primary_key_checked = False

    for table in connector.list_tables(schema):
        if (_norm(table.schema), _norm(table.name)) not in modeled:
            report.items.append(
                DriftItem(
                    "table_unmodeled",
                    "-",
                    f"table {_qualified(table)} is in the database but no model "
                    "references it",
                )
            )
    return report


def _qualified(table: TableRef) -> str:
    parts = [p for p in (table.catalog, table.schema, table.name) if p]
    return ".".join(parts)


def render_text(report: DriftReport) -> str:
    lines = []
    for item in report.items:
        target = f"model {item.model}" if item.model != "-" else "database"
        lines.append(f"✗ {target}: {item.detail}")
    for note in report.skipped:
        lines.append(f"· skipped {note}")
    if not report.primary_key_checked:
        lines.append("· primary keys not compared: this connector cannot report keys")
    summary = (
        f"Checked {len(report.checked)} model(s) against {report.data_source}: "
        + (f"{len(report.items)} difference(s)." if report.items else "no drift.")
    )
    lines.append(summary)
    return "\n".join(lines)
