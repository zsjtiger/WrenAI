"""Mine reusable SQL attributes from the confirmed query history.

Source: the NL-to-SQL pairs in ``knowledge/sql/*.md``, which people have
confirmed. Each query is parsed and yields two kinds of expression:

* **aggregate**: ``SUM``, ``AVG``, ``MIN``, ``MAX``, ``COUNT`` (including
  ``COUNT(DISTINCT x)`` and ``COUNT(*)``);
* **filter**: a WHERE comparison between a column and a literal, or an ``IN`` /
  ``BETWEEN`` on a column.

An expression scores the number of distinct queries it appears in. Expressions
below ``min_occurrences`` are dropped, and each model keeps its top ``top_n``.
A model attribution needs the expression's column to belong to exactly one
model the query reads from; otherwise the attribute is attributed to the query
itself (model ``None``).

Rules give each attribute a name (``sum(amount)`` -> ``total_amount``). With a
configured model, the model may keep or reject each candidate and may rename it.
Its reply is used only for known candidates. Output goes to
``draft/attributes.yml``, and ``models/`` is never changed.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlglot import exp, parse_one

from janus.llm import LlmConfig, LlmError, complete_json

ATTRIBUTES_FILE = "attributes.yml"
DEFAULT_MIN_OCCURRENCES = 2
DEFAULT_TOP_N = 10

KIND_AGGREGATE = "aggregate"
KIND_FILTER = "filter"

STATUS_SUGGESTED = "suggested"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"

_AGGREGATES = (exp.Sum, exp.Avg, exp.Min, exp.Max, exp.Count)
_COMPARISONS = (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)


@dataclass
class Candidate:
    kind: str
    expression: str  # normalized SQL, the identity of the attribute
    name: str
    model: str | None
    occurrences: int = 0
    queries: list[str] = field(default_factory=list)


@dataclass
class Attribute:
    model: str | None
    name: str
    expression: str
    kind: str
    occurrences: int
    queries: list[str]
    status: str = STATUS_SUGGESTED
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MiningResult:
    attributes: list[Attribute] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    queries_scanned: int = 0


# ── naming ──────────────────────────────────────────────────────────────────


def _snake(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "value"


def _column_name(node: exp.Expression) -> str | None:
    col = node.find(exp.Column) if not isinstance(node, exp.Column) else node
    return col.name.lower() if col is not None and col.name else None


def _rule_name(node: exp.Expression) -> str:
    """The attribute name a rule gives an aggregate or a filter node."""
    if isinstance(node, _AGGREGATES):
        target = node.this
        if isinstance(node, exp.Count):
            if isinstance(target, exp.Star) or target is None:
                return "row_count"
            distinct = isinstance(target, exp.Distinct)
            col = _column_name(target) or "value"
            return f"distinct_{col}_count" if distinct else f"{col}_count"
        col = _column_name(node) or "value"
        prefix = {exp.Sum: "total", exp.Avg: "average", exp.Min: "min", exp.Max: "max"}[
            type(node)
        ]
        return f"{prefix}_{col}"
    if isinstance(node, exp.In):
        return f"{_column_name(node) or 'value'}_in_list"
    if isinstance(node, exp.Between):
        return f"{_column_name(node) or 'value'}_range"
    col = _column_name(node) or "value"
    literal = node.expression if isinstance(node, exp.Binary) else None
    value = _snake(literal.name) if isinstance(literal, exp.Literal) else "value"
    if isinstance(node, exp.EQ):
        return f"{col}_{value}"
    op = {
        exp.NEQ: "not",
        exp.GT: "above",
        exp.GTE: "from",
        exp.LT: "below",
        exp.LTE: "to",
    }
    return f"{col}_{op[type(node)]}_{value}"


# ── extraction ──────────────────────────────────────────────────────────────


def _normalize(node: exp.Expression, dialect: str) -> str:
    """The expression's identity: SQL text with table qualifiers removed, so that
    ``sum(f.net_amount)`` and ``sum(net_amount)`` are the same measure."""
    bare = node.copy()
    for col in bare.find_all(exp.Column):
        col.set("table", None)
    return bare.sql(dialect=dialect).lower()


def _tables_of(tree: exp.Expression) -> list[str]:
    return sorted({t.name for t in tree.find_all(exp.Table) if t.name})


def _expressions(tree: exp.Expression, dialect: str) -> list[exp.Expression]:
    """Aggregates anywhere in the query, plus filter predicates in WHERE clauses."""
    found: list[exp.Expression] = []
    for node in tree.find_all(*_AGGREGATES):
        found.append(node)
    where = tree.args.get("where")
    if where is not None:
        for node in where.this.find_all(_COMPARISONS, exp.In, exp.Between):
            left = node.this
            if isinstance(left, exp.Column) and (
                isinstance(node, exp.In | exp.Between)
                or isinstance(node.expression, exp.Literal)
            ):
                found.append(node)
    return found


def _owner(
    column: str | None, tables: list[str], columns_by_model: dict[str, set[str]]
) -> str | None:
    """The one model among ``tables`` that has ``column``, or ``None`` if not unique."""
    if column is None:
        return None
    owners = [t for t in tables if column in columns_by_model.get(t, set())]
    return owners[0] if len(owners) == 1 else None


def mine_attributes(
    pairs: list[dict],
    models: list[dict],
    dialect: str,
    *,
    min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
    top_n: int = DEFAULT_TOP_N,
) -> MiningResult:
    """Count expressions across confirmed queries and keep the frequent ones."""
    result = MiningResult()
    columns_by_model = {
        str(m["name"]).lower(): {str(c["name"]).lower() for c in m.get("columns") or []}
        for m in models
        if m.get("name")
    }
    candidates: dict[tuple[str, str | None], Candidate] = {}
    for pair in pairs:
        sql = str(pair.get("sql") or "").strip()
        path = str(pair.get("path") or pair.get("nl") or "")
        if not sql:
            continue
        try:
            tree = parse_one(sql, dialect=dialect)
        except Exception as exc:  # noqa: BLE001 - one bad query must not stop the pass
            result.notes.append(f"{path}: could not parse SQL ({type(exc).__name__})")
            continue
        result.queries_scanned += 1
        tables = [t.lower() for t in _tables_of(tree)]
        seen_in_query: set[tuple[str, str | None]] = set()
        for node in _expressions(tree, dialect):
            key_text = _normalize(node, dialect)
            column = _column_name(node)
            model = _owner(column, tables, columns_by_model)
            kind = (
                KIND_FILTER
                if isinstance(node, _COMPARISONS + (exp.In, exp.Between))
                else KIND_AGGREGATE
            )
            key = (key_text, model)
            if key in seen_in_query:
                continue
            seen_in_query.add(key)
            cand = candidates.get(key)
            if cand is None:
                cand = Candidate(kind, key_text, _rule_name(node), model)
                candidates[key] = cand
            cand.occurrences += 1
            cand.queries.append(path)

    kept = [c for c in candidates.values() if c.occurrences >= min_occurrences]
    by_model: dict[str | None, list[Candidate]] = {}
    for cand in kept:
        by_model.setdefault(cand.model, []).append(cand)
    for model, items in by_model.items():
        items.sort(key=lambda c: (-c.occurrences, c.expression))
        for cand in items[:top_n]:
            result.attributes.append(
                Attribute(
                    model=model,
                    name=cand.name,
                    expression=cand.expression,
                    kind=cand.kind,
                    occurrences=cand.occurrences,
                    queries=sorted(set(cand.queries)),
                )
            )
        if len(items) > top_n:
            result.notes.append(
                f"{model or 'query-level'}: {len(items) - top_n} lower-ranked "
                "expression(s) left out (top_n)"
            )
    result.attributes.sort(key=lambda a: (a.model or "", -a.occurrences, a.expression))
    return result


# ── optional model judgement ────────────────────────────────────────────────

_JUDGE_SYSTEM = (
    "You review SQL expressions that recur in confirmed queries over a semantic layer. "
    "For each one, decide whether it is a reusable business measure or filter worth "
    "naming, and give it a short snake_case name. Use only the text you are given. "
    'Reply with a JSON object {"attributes": {"<expression>": {"worth_naming": true or '
    'false, "name": "<snake_case name>"}}} and nothing else.'
)


def judge_with_model(result: MiningResult, llm: LlmConfig) -> None:
    """Ask the model to keep, reject, or rename each attribute. Failures keep the rules."""
    if not result.attributes:
        return
    listing = [
        {
            "expression": a.expression,
            "kind": a.kind,
            "model": a.model,
            "occurrences": a.occurrences,
        }
        for a in result.attributes
    ]
    try:
        reply = complete_json(
            llm,
            _JUDGE_SYSTEM,
            f"Expressions (JSON): {json.dumps(listing, ensure_ascii=False)}",
        )
    except LlmError as exc:
        result.notes.append(f"model unavailable ({exc}); kept the rule attributes")
        return
    verdicts = reply.get("attributes")
    if not isinstance(verdicts, dict):
        result.notes.append(
            'model reply has no "attributes" object; kept the rule attributes'
        )
        return
    for attr in result.attributes:
        verdict = verdicts.get(attr.expression)
        if not isinstance(verdict, dict):
            continue
        if verdict.get("worth_naming") is False:
            attr.status = STATUS_REJECTED
            attr.reasons.append("model: not worth naming")
            continue
        new_name = verdict.get("name")
        if isinstance(new_name, str) and re.fullmatch(
            r"[a-z][a-z0-9_]*", new_name.strip()
        ):
            attr.name = new_name.strip()
            attr.reasons.append("model: renamed")
        if verdict.get("worth_naming") is True:
            attr.status = STATUS_CONFIRMED
            attr.reasons.append("model: worth naming")


# ── writing ─────────────────────────────────────────────────────────────────


def load_pairs(project_path: Path) -> list[dict]:
    from janus.memory.markdown import load_query_pairs  # noqa: PLC0415

    return load_query_pairs(project_path)


def write_attributes(project_path: Path, result: MiningResult) -> Path:
    draft = project_path / "draft"
    draft.mkdir(parents=True, exist_ok=True)
    path = draft / ATTRIBUTES_FILE
    path.write_text(
        yaml.safe_dump(
            {
                "attributes": [a.to_dict() for a in result.attributes],
                "queries_scanned": result.queries_scanned,
                "notes": result.notes,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return path
