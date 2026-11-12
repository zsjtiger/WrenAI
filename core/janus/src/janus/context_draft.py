"""Draft MDL models from a live database, and promote them into the project.

``generate_drafts`` writes candidate models to ``<project>/draft/models/<name>/``
and candidate relationships to ``<project>/draft/relationships.yml``. It only
does deterministic work (tables, columns, types, keys, foreign keys) and never
touches ``models/`` or ``relationships.yml``.

Every draft model carries ``properties.draft: "true"``. ``apply_draft`` moves
one model out of ``draft/`` into ``models/``, removes that marker, adds the
draft relationships whose both ends now exist, and validates the project. If
validation fails the move is rolled back.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from janus.llm import LlmConfig, LlmError, complete_json
from janus.mdl.cte_rewriter import get_sqlglot_dialect
from janus.model.data_source import DataSource
from janus.type_mapping import parse_type

DRAFT_DIR = "draft"
DRAFT_PROPERTY = "draft"


@dataclass
class DraftResult:
    models: list[str] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _model_name(table_name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]", "_", table_name).strip("_").lower()
    return name or "table"


def _dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _modeled_tables(models: list[dict]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for model in models:
        tref = model.get("table_reference") or {}
        if tref.get("table"):
            result.add(
                (str(tref.get("schema") or "").lower(), str(tref["table"]).lower())
            )
    return result


def generate_drafts(
    project_path: Path,
    connector: Any,
    data_source: DataSource,
    *,
    schema: str | None = None,
    suggest_terms: bool = False,
    llm: LlmConfig | None = None,
) -> DraftResult:
    """Write draft models and relationships for unmodeled tables.

    With ``suggest_terms`` every column gets a ``description``. The model in
    ``llm`` writes them when it is available; otherwise, or for any column it
    leaves out, ``deterministic_description`` is used. Each column records which
    one it got in ``properties.description_source``. Only column names and types
    are sent to the model, never row values.
    """
    from janus.context import load_models  # noqa: PLC0415

    dialect = get_sqlglot_dialect(data_source)
    existing = load_models(project_path)
    existing_names = {m.get("name") for m in existing}
    modeled = _modeled_tables(existing)
    result = DraftResult()

    draft_root = project_path / DRAFT_DIR
    draft_models_dir = draft_root / "models"
    drafted: dict[tuple[str, str], str] = {}  # (schema, table) -> model name
    foreign_keys: list[tuple[str, Any]] = []
    used_names = set(existing_names)

    for table in connector.list_tables(schema):
        key = (str(table.schema or "").lower(), table.name.lower())
        if key in modeled:
            result.skipped.append(f"{table.name}: already modeled")
            continue

        name = _model_name(table.name)
        if name in used_names:
            name = f"{name}_{_model_name(table.schema or 'db')}"
        if name in used_names:
            result.skipped.append(f"{table.name}: model name '{name}' is taken")
            continue
        used_names.add(name)

        columns = connector.list_columns(table)
        keys = connector.list_keys(table)
        pk = keys.primary_key
        descriptions = _describe_columns(
            table, columns, suggest_terms=suggest_terms, llm=llm, result=result
        )
        if len(pk) > 1:
            result.notes.append(
                f"{name}: composite primary key {list(pk)} left out (MDL keys "
                "are single columns)"
            )
        model = {
            "name": name,
            "table_reference": {
                "catalog": table.catalog or "",
                "schema": table.schema or "",
                "table": table.name,
            },
            "columns": [
                {
                    "name": col.name,
                    "type": _mdl_type(col.data_type, dialect),
                    "is_calculated": False,
                    "not_null": not col.nullable,
                    "is_primary_key": len(pk) == 1 and col.name in pk,
                    **_column_description(descriptions, col.name),
                    "properties": _column_properties(descriptions, col.name),
                }
                for col in columns
            ],
            "cached": False,
            "properties": {DRAFT_PROPERTY: "true"},
        }
        if len(pk) == 1:
            model["primary_key"] = pk[0]

        model_dir = draft_models_dir / name
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / "metadata.yml").write_text(_dump(model), encoding="utf-8")
        drafted[key] = name
        result.models.append(name)

        for fk in keys.foreign_keys:
            foreign_keys.append((name, fk))

    # Resolve foreign keys against drafted and already-modeled tables.
    modeled_names = {m.get("name"): m for m in existing}
    relationships: list[dict] = []
    for from_name, fk in foreign_keys:
        ref_key = (str(fk.ref_table.schema or "").lower(), fk.ref_table.name.lower())
        to_name = drafted.get(ref_key)
        if to_name is None:
            to_name = next(
                (
                    n
                    for n, m in modeled_names.items()
                    if (
                        str(
                            (m.get("table_reference") or {}).get("schema") or ""
                        ).lower(),
                        str(
                            (m.get("table_reference") or {}).get("table") or ""
                        ).lower(),
                    )
                    == ref_key
                ),
                None,
            )
        if to_name is None:
            result.notes.append(
                f"{from_name}: foreign key {fk.name} points at "
                f"{fk.ref_table.name}, which is neither drafted nor modeled"
            )
            continue
        conditions = " AND ".join(
            f"{from_name}.{c} = {to_name}.{r}"
            for c, r in zip(fk.columns, fk.ref_columns, strict=True)
        )
        relationships.append(
            {
                "name": f"{from_name}_{to_name}_{'_'.join(fk.columns)}",
                "models": [from_name, to_name],
                "join_type": "many_to_one",
                "condition": conditions,
            }
        )

    if relationships:
        draft_root.mkdir(parents=True, exist_ok=True)
        (draft_root / "relationships.yml").write_text(
            _dump({"relationships": relationships}), encoding="utf-8"
        )
        result.relationships = [r["name"] for r in relationships]
    return result


DESCRIPTION_SOURCE = "description_source"

_DESCRIPTION_SYSTEM = (
    "You document the columns of one database table for a semantic layer. "
    "For each column, write one short sentence saying what it represents in "
    "business terms. Use only the names and types you are given; if a name is "
    "not self-explanatory, say what it probably holds and that it is uncertain. "
    'Reply with a JSON object of the form {"descriptions": {"<column>": '
    '"<sentence>"}} and nothing else.'
)


def deterministic_description(column_name: str, data_type: str) -> str:
    """The fallback description: the column name in words, with its type."""
    words = re.sub(r"[_\s]+", " ", column_name).strip()
    if not words:
        words = column_name
    return f"{words[:1].upper()}{words[1:]} ({data_type})"


def _describe_columns(
    table: Any,
    columns: list[Any],
    *,
    suggest_terms: bool,
    llm: LlmConfig | None,
    result: DraftResult,
) -> dict[str, dict[str, str]]:
    """Per-column ``{"description", DESCRIPTION_SOURCE}`` for one table.

    Returns an empty mapping when ``suggest_terms`` is off, so drafts keep their
    original shape. Failures are recorded in ``result.notes``; they never raise.
    """
    if not suggest_terms or not columns:
        return {}

    suggested: dict[str, str] = {}
    if llm is None:
        result.notes.append(
            f"{table.name}: no model configured (set JANUS_LLM_BASE_URL and "
            "JANUS_LLM_MODEL); used deterministic descriptions"
        )
    else:
        try:
            suggested = _ask_model(table, columns, llm)
        except LlmError as exc:
            result.notes.append(
                f"{table.name}: model unavailable ({exc}); used deterministic "
                "descriptions"
            )

    described: dict[str, dict[str, str]] = {}
    for col in columns:
        text = suggested.get(col.name)
        if text:
            source = "llm"
        else:
            text = deterministic_description(col.name, col.data_type)
            source = "deterministic"
        described[col.name] = {"description": text, DESCRIPTION_SOURCE: source}
    return described


def _ask_model(table: Any, columns: list[Any], llm: LlmConfig) -> dict[str, str]:
    """Ask the model for descriptions. Returns only usable, known column names."""
    listing = [{"name": c.name, "type": c.data_type} for c in columns]
    user = (
        f"Table: {table.name}\n"
        f"Columns (JSON): {json.dumps(listing, ensure_ascii=False)}"
    )
    payload = complete_json(llm, _DESCRIPTION_SYSTEM, user)
    raw = payload.get("descriptions")
    if not isinstance(raw, dict):
        raise LlmError('model reply has no "descriptions" object')
    known = {c.name for c in columns}
    return {
        name: text.strip()
        for name, text in raw.items()
        if name in known and isinstance(text, str) and text.strip()
    }


def _column_description(descriptions: dict[str, dict[str, str]], name: str) -> dict:
    """The column's top-level ``description`` (absent when descriptions are off)."""
    entry = descriptions.get(name)
    return {"description": entry["description"]} if entry else {}


def _column_properties(descriptions: dict[str, dict[str, str]], name: str) -> dict:
    """Column ``properties``: the description source, when descriptions are on."""
    entry = descriptions.get(name)
    if not entry:
        return {}
    return {DESCRIPTION_SOURCE: entry[DESCRIPTION_SOURCE]}


def _mdl_type(data_type: str, dialect: str) -> str:
    try:
        return parse_type(data_type, dialect)
    except Exception:  # noqa: BLE001 - keep the raw type when it does not parse
        return data_type


def _draft_relationships(project_path: Path) -> list[dict]:
    path = project_path / DRAFT_DIR / "relationships.yml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rels = data.get("relationships") if isinstance(data, dict) else None
    return [r for r in rels or [] if isinstance(r, dict)]


def _write_draft_relationships(project_path: Path, rels: list[dict]) -> None:
    path = project_path / DRAFT_DIR / "relationships.yml"
    if rels:
        path.write_text(_dump({"relationships": rels}), encoding="utf-8")
    elif path.exists():
        path.unlink()


def list_drafts(project_path: Path) -> list[str]:
    models_dir = project_path / DRAFT_DIR / "models"
    if not models_dir.is_dir():
        return []
    return sorted(p.name for p in models_dir.iterdir() if (p / "metadata.yml").exists())


def apply_draft(project_path: Path, name: str) -> list[str]:
    """Promote draft model ``name`` into ``models/`` and return added relationships.

    Raises ``ValueError`` if the draft is missing, the target already exists,
    or the project fails validation after the move (the move is rolled back).
    """
    from janus.context import validate_project  # noqa: PLC0415

    src = project_path / DRAFT_DIR / "models" / name
    dst = project_path / "models" / name
    if not (src / "metadata.yml").exists():
        raise ValueError(f"no draft model named '{name}'")
    if dst.exists():
        raise ValueError(f"models/{name} already exists; remove or rename it first")

    rel_file = project_path / "relationships.yml"
    original_rel_text = (
        rel_file.read_text(encoding="utf-8") if rel_file.exists() else None
    )
    original_draft_rels = _draft_relationships(project_path)

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    meta_path = dst / "metadata.yml"
    model = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    props = dict(model.get("properties") or {})
    props.pop(DRAFT_PROPERTY, None)
    model["properties"] = props
    meta_path.write_text(_dump(model), encoding="utf-8")

    from janus.context import load_models  # noqa: PLC0415

    live_names = {m.get("name") for m in load_models(project_path)}
    applied: list[dict] = []
    remaining: list[dict] = []
    for rel in original_draft_rels:
        models = rel.get("models") or []
        if name in models and all(m in live_names for m in models):
            applied.append(rel)
        else:
            remaining.append(rel)

    if applied:
        existing_doc: dict = {}
        if original_rel_text is not None:
            existing_doc = yaml.safe_load(original_rel_text) or {}
        existing_rels = list(existing_doc.get("relationships") or [])
        known = {r.get("name") for r in existing_rels if isinstance(r, dict)}
        existing_rels.extend(r for r in applied if r.get("name") not in known)
        rel_file.write_text(_dump({"relationships": existing_rels}), encoding="utf-8")

    _write_draft_relationships(project_path, remaining)

    errors = [e for e in validate_project(project_path) if e.level == "error"]
    if errors:
        shutil.move(str(dst), str(src))
        _write_draft_relationships(project_path, original_draft_rels)
        if original_rel_text is None:
            if rel_file.exists():
                rel_file.unlink()
        else:
            rel_file.write_text(original_rel_text, encoding="utf-8")
        raise ValueError(
            "validation failed after applying draft; nothing was changed: "
            + "; ".join(str(e) for e in errors)
        )
    return [r["name"] for r in applied]
