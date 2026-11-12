"""Business terms for models and display names for their columns.

Rules work from names alone:

* a model's term is its name without a warehouse prefix (``dim_``, ``fact_``,
  ``tbl_``, ``stg_``, ``raw_``), split into words, singular, and title-cased;
* a column's display name expands common abbreviations (``cust`` -> Customer,
  ``qty`` -> Quantity) and writes ``id`` as ``ID``;
* the model's raw name is kept as an alias when it differs from the term.

With ``refine`` and a configured model, the model may replace the term and the
display names. Its reply is accepted only for known models and columns, and a
failed call keeps the rule result for that model.

Output goes to ``draft/terms.yml``; ``models/`` is never changed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from janus.llm import LlmConfig, LlmError, complete_json
from janus.semantic_fk import _singular

TERMS_FILE = "terms.yml"
SOURCE_RULE = "rule"
SOURCE_MODEL = "model"

_PREFIXES = ("tbl_", "dim_", "fact_", "stg_", "raw_", "v_")
_ABBREVIATIONS = {
    "cust": "customer",
    "qty": "quantity",
    "amt": "amount",
    "dt": "date",
    "num": "number",
    "desc": "description",
    "addr": "address",
    "tel": "phone",
    "pct": "percent",
    "prod": "product",
    "acct": "account",
    "txn": "transaction",
    "ts": "timestamp",
}
_ACRONYMS = {"id", "url", "sku", "api", "ip", "usd", "eur"}


@dataclass
class ColumnTerm:
    name: str
    display_name: str
    source: str = SOURCE_RULE


@dataclass
class ModelTerm:
    model: str
    term: str
    aliases: list[str] = field(default_factory=list)
    columns: list[ColumnTerm] = field(default_factory=list)
    source: str = SOURCE_RULE
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        return out


def _words(name: str) -> list[str]:
    lowered = name.strip()
    for prefix in _PREFIXES:
        if lowered.lower().startswith(prefix) and len(lowered) > len(prefix):
            lowered = lowered[len(prefix) :]
            break
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", lowered)
    return [w for w in re.split(r"[_\s\-]+", spaced.lower()) if w]


def _title(word: str) -> str:
    if word in _ACRONYMS:
        return word.upper()
    return word[:1].upper() + word[1:]


def humanize_model(name: str) -> str:
    """``dim_order_items`` -> ``Order Item``."""
    words = _words(name)
    if not words:
        return name
    words[-1] = _singular(words[-1])
    return " ".join(_title(w) for w in words)


def humanize_column(name: str) -> str:
    """``cust_id`` -> ``Customer ID``; ``qty`` -> ``Quantity``."""
    words = _words(name)
    if not words:
        return name
    expanded = [_ABBREVIATIONS.get(w, w) for w in words]
    return " ".join(_title(w) for w in expanded)


def rule_terms(models: list[dict]) -> list[ModelTerm]:
    """Rule-based terms for every model, in project order."""
    out: list[ModelTerm] = []
    for model in models:
        name = str(model.get("name") or "")
        if not name:
            continue
        term = humanize_model(name)
        aliases = []
        raw = name.replace("_", " ").title()
        if raw != term and raw not in aliases:
            aliases.append(raw)
        columns = [
            ColumnTerm(str(c["name"]), humanize_column(str(c["name"])))
            for c in model.get("columns") or []
            if c.get("name")
        ]
        out.append(ModelTerm(name, term, aliases, columns))
    return out


_REFINE_SYSTEM = (
    "You name business concepts for a semantic layer. For each table, give one short "
    "business term and a display name for each column, using only the names and types "
    'you are given. Reply with a JSON object of the form {"tables": {"<table>": '
    '{"term": "<term>", "columns": {"<column>": "<display name>"}}}} and nothing else.'
)


def _refine(models: list[dict], llm: LlmConfig) -> dict[str, Any]:
    listing = [
        {
            "table": m["name"],
            "columns": [
                {"name": c["name"], "type": str(c.get("type") or "")}
                for c in m.get("columns") or []
                if c.get("name")
            ],
        }
        for m in models
    ]
    reply = complete_json(
        llm, _REFINE_SYSTEM, f"Tables (JSON): {json.dumps(listing, ensure_ascii=False)}"
    )
    tables = reply.get("tables")
    if not isinstance(tables, dict):
        raise LlmError('model reply has no "tables" object')
    return tables


def apply_refinement(terms: list[ModelTerm], tables: dict[str, Any]) -> int:
    """Apply model-suggested terms and display names. Returns how many changed."""
    changed = 0
    for term in terms:
        suggestion = tables.get(term.model)
        if not isinstance(suggestion, dict):
            continue
        new_term = suggestion.get("term")
        if isinstance(new_term, str) and new_term.strip():
            term.term = new_term.strip()
            term.source = SOURCE_MODEL
            changed += 1
        cols = suggestion.get("columns")
        if isinstance(cols, dict):
            for col in term.columns:
                display = cols.get(col.name)
                if isinstance(display, str) and display.strip():
                    col.display_name = display.strip()
                    col.source = SOURCE_MODEL
                    changed += 1
    return changed


def build_terms(
    models: list[dict],
    *,
    llm: LlmConfig | None = None,
) -> tuple[list[ModelTerm], list[str]]:
    """Rule terms, refined by the model when one is given. Returns ``(terms, notes)``."""
    terms = rule_terms(models)
    notes: list[str] = []
    if llm is None or not models:
        return terms, notes
    try:
        tables = _refine(models, llm)
    except LlmError as exc:
        notes.append(f"model unavailable ({exc}); kept the rule terms")
        return terms, notes
    apply_refinement(terms, tables)
    return terms, notes


def write_terms(project_path: Path, terms: list[ModelTerm], notes: list[str]) -> Path:
    """Write ``draft/terms.yml``. Returns the path."""
    draft = project_path / "draft"
    draft.mkdir(parents=True, exist_ok=True)
    path = draft / TERMS_FILE
    path.write_text(
        yaml.safe_dump(
            {"terms": [t.to_dict() for t in terms], "notes": notes},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path
