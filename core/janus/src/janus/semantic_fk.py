"""Infer foreign keys the project does not declare, and detect bridge tables.

Input is the project's MDL models and declared relationships, so this runs
without a database connection. Output is written under ``draft/`` and never
touches ``models/`` or ``relationships.yml``.

Ranking, in order:

1. **Name rule.** A column ``<stem>_id`` (or ``<stem>id``) matches a model whose
   name, or singular name, equals ``<stem>``. A partial prefix match scores lower.
2. **Type rule.** The column and the target's single primary key must share a
   type family. Incompatible types are never candidates.
3. **Embedding rerank** (optional, when the embedding API is configured). It
   only breaks ties between targets that scored the same.
4. **Model confirmation** (optional, ``--confirm-with-model``). The model answers
   yes or no per candidate, from names and types only. A failed call keeps the
   rule result.

A column that stays tied without a usable embedding is reported as ``ambiguous``
and gets no relationship. Bridge tables are models whose every column is a
foreign key to a different table; each pair of their targets gets a join.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from janus.llm import LlmConfig, LlmError, complete_json
from janus.mdl.cte_rewriter import get_sqlglot_dialect
from janus.model.data_source import DataSource
from janus.type_mapping import parse_type

SUGGESTIONS_FILE = "fk_suggestions.yml"
BRIDGES_FILE = "bridges.yml"
RELATIONSHIPS_FILE = "relationships.yml"

RULE_EXACT = 0.8
RULE_PARTIAL = 0.5
MIN_EMBEDDING_MARGIN = 0.05

STATUS_SUGGESTED = "suggested"  # rule result, not confirmed by a model
STATUS_CONFIRMED = "confirmed"  # the model agreed
STATUS_REJECTED = "rejected"  # the model disagreed
STATUS_AMBIGUOUS = "ambiguous"  # tied; no relationship written

_ID_SUFFIXES = ("_id", "_key", "_fk")
_INTEGER_TYPES = {"INT", "INTEGER", "INT4", "INT8", "BIGINT", "SMALLINT", "TINYINT"}
_TEXT_TYPES = {"VARCHAR", "TEXT", "STRING", "CHAR", "NVARCHAR"}


@dataclass(frozen=True)
class Candidate:
    model: str
    column: str
    score: float
    reason: str


@dataclass
class Suggestion:
    model: str
    column: str
    target_model: str
    target_column: str
    score: float
    source: str  # "rule" or "embedding"
    status: str
    reasons: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Bridge:
    bridge: str
    models: tuple[str, str]
    attach_to: tuple[str, str]
    join_sql: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge": self.bridge,
            "models": list(self.models),
            "attach_to": list(self.attach_to),
            "join_sql": self.join_sql,
        }


@dataclass
class InferenceResult:
    suggestions: list[Suggestion] = field(default_factory=list)
    bridges: list[Bridge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ── names and types ─────────────────────────────────────────────────────────


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ss"):
        return word
    if word.endswith("s") and len(word) > 3:
        return word[:-1]
    return word


def _model_forms(name: str) -> set[str]:
    lower = name.lower()
    forms = {lower, _singular(lower)}
    if "_" in lower:
        head, _, tail = lower.rpartition("_")
        forms.add(f"{head}_{_singular(tail)}")
    return forms


def _stem(column: str) -> str | None:
    lower = column.lower()
    for suffix in _ID_SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix):
            return lower[: -len(suffix)]
    # ``custid`` -> ``cust``. Keep stems of 4+ characters so ``paid`` is not ``pa``.
    if lower.endswith("id") and len(lower) - 2 >= 4:
        return lower[:-2]
    return None


def _type_family(data_type: str | None, dialect: str) -> str | None:
    if not data_type:
        return None
    try:
        base = parse_type(str(data_type), dialect)
    except Exception:  # noqa: BLE001 - an unparseable type is simply unknown
        base = str(data_type)
    base = re.split(r"[\s(]", base.strip().upper(), maxsplit=1)[0]
    if base in _INTEGER_TYPES:
        return "INTEGER"
    if base in _TEXT_TYPES:
        return "TEXT"
    return base


_CONDITION = re.compile(r"(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)")


def _declared_targets(relationships: list[dict]) -> dict[str, dict[str, str]]:
    """``model -> {column: target model}`` from declared relationship conditions."""
    targets: dict[str, dict[str, str]] = {}
    for rel in relationships:
        for left_m, left_c, right_m, right_c in _CONDITION.findall(
            str(rel.get("condition") or "")
        ):
            targets.setdefault(left_m.lower(), {})[left_c.lower()] = right_m.lower()
            targets.setdefault(right_m.lower(), {})[right_c.lower()] = left_m.lower()
    return targets


# ── rules ───────────────────────────────────────────────────────────────────


def _targets(models: list[dict], dialect: str) -> dict[str, tuple[str, str]]:
    """Models with a single-column primary key: ``model -> (pk column, pk type)``."""
    targets: dict[str, tuple[str, str]] = {}
    for model in models:
        pk = model.get("primary_key")
        if not isinstance(pk, str) or not pk:
            continue
        pk_col = next(
            (c for c in model.get("columns") or [] if str(c.get("name")) == pk), None
        )
        if pk_col is None:
            continue
        targets[str(model["name"])] = (pk, str(pk_col.get("type") or ""))
    return targets


def _rule_candidates(
    model: dict, column: dict, targets: dict[str, tuple[str, str]], dialect: str
) -> list[Candidate]:
    stem = _stem(str(column.get("name") or ""))
    if stem is None:
        return []
    family = _type_family(column.get("type"), dialect)
    out: list[Candidate] = []
    for target, (pk_col, pk_type) in targets.items():
        if target == model["name"]:
            continue
        forms = _model_forms(target)
        if stem in forms:
            score, reason = RULE_EXACT, f"name '{stem}' matches model '{target}'"
        elif len(stem) >= 4 and any(form.startswith(stem) for form in forms):
            score, reason = (
                RULE_PARTIAL,
                f"name '{stem}' is a prefix of model '{target}'",
            )
        else:
            continue
        target_family = _type_family(pk_type, dialect)
        if family is None or target_family is None or family != target_family:
            continue
        out.append(
            Candidate(target, pk_col, score, reason + f", types match ({family})")
        )
    return out


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _rerank_with_embeddings(
    embedder: Any,
    model: str,
    column: str,
    data_type: str,
    tied: list[Candidate],
    targets: dict[str, tuple[str, str]],
) -> Candidate | None:
    """The tied candidate closest to the column, when it clearly wins."""
    query = embedder.compute_query_embeddings(f"{model}.{column} ({data_type})")[0]
    names = [f"{c.model} (primary key {targets[c.model][0]})" for c in tied]
    vectors = embedder.compute_source_embeddings(names)
    scored = sorted(
        zip(tied, (_cosine(list(query), list(v)) for v in vectors), strict=True),
        key=lambda pair: pair[1],
        reverse=True,
    )
    if len(scored) > 1 and scored[0][1] - scored[1][1] < MIN_EMBEDDING_MARGIN:
        return None
    return scored[0][0]


def _embedder_from_env():
    """The API embedder when configured; ``None`` otherwise."""
    from janus.memory.api_embeddings import (  # noqa: PLC0415
        ApiEmbeddings,
        load_api_embedding_config,
    )

    cfg = load_api_embedding_config()
    return ApiEmbeddings(cfg) if cfg is not None else None


def _confirm(
    llm: LlmConfig, model: str, column: str, data_type: str, target: str, target_pk: str
) -> tuple[bool, str]:
    """Ask the model whether the column references the target's key."""
    system = (
        "You check whether a column in one table is a foreign key to the primary key "
        "of another table. Use only the names and types you are given. Reply with a "
        'JSON object {"is_foreign_key": true or false, "reason": "<short reason>"} '
        "and nothing else."
    )
    user = json.dumps(
        {
            "column": {"table": model, "name": column, "type": data_type},
            "target": {"table": target, "primary_key": target_pk},
        },
        ensure_ascii=False,
    )
    reply = complete_json(llm, system, user)
    verdict = reply.get("is_foreign_key")
    if not isinstance(verdict, bool):
        raise LlmError('model reply has no boolean "is_foreign_key"')
    return verdict, str(reply.get("reason") or "")


# ── the pass ────────────────────────────────────────────────────────────────


def infer_foreign_keys(
    models: list[dict],
    relationships: list[dict],
    data_source: DataSource,
    *,
    llm: LlmConfig | None = None,
    embedder: Any | None = None,
) -> InferenceResult:
    """Suggest undeclared foreign keys and the bridge tables they form."""
    dialect = get_sqlglot_dialect(data_source)
    result = InferenceResult()
    targets = _targets(models, dialect)
    declared = _declared_targets(relationships)
    by_name = {str(m["name"]): m for m in models}

    for model in models:
        mname = str(model["name"])
        for column in model.get("columns") or []:
            cname = str(column.get("name") or "")
            if not cname or cname.lower() in declared.get(mname.lower(), {}):
                continue
            candidates = _rule_candidates(model, column, targets, dialect)
            if not candidates:
                continue
            top = max(c.score for c in candidates)
            best = [c for c in candidates if c.score == top]
            suggestion = None
            if len(best) == 1:
                chosen = best[0]
                suggestion = Suggestion(
                    mname,
                    cname,
                    chosen.model,
                    chosen.column,
                    chosen.score,
                    "rule",
                    STATUS_SUGGESTED,
                    [chosen.reason],
                )
            elif embedder is not None:
                try:
                    picked = _rerank_with_embeddings(
                        embedder,
                        mname,
                        cname,
                        str(column.get("type") or ""),
                        best,
                        targets,
                    )
                except Exception as exc:  # noqa: BLE001 - embeddings are optional
                    result.notes.append(
                        f"{mname}.{cname}: embedding rerank unavailable ({exc}); "
                        "left ambiguous"
                    )
                    picked = None
                if picked is not None:
                    suggestion = Suggestion(
                        mname,
                        cname,
                        picked.model,
                        picked.column,
                        picked.score,
                        "embedding",
                        STATUS_SUGGESTED,
                        [
                            picked.reason,
                            "chosen by embedding similarity among tied targets",
                        ],
                    )
            if suggestion is None:
                suggestion = Suggestion(
                    mname,
                    cname,
                    best[0].model,
                    best[0].column,
                    top,
                    "rule",
                    STATUS_AMBIGUOUS,
                    [f"tied at score {top}"],
                    sorted(c.model for c in best),
                )
            result.suggestions.append(suggestion)

    if llm is not None:
        for suggestion in result.suggestions:
            if suggestion.status != STATUS_SUGGESTED:
                continue
            column = _column_of(by_name, suggestion.model, suggestion.column)
            try:
                is_fk, reason = _confirm(
                    llm,
                    suggestion.model,
                    suggestion.column,
                    str(column.get("type") or ""),
                    suggestion.target_model,
                    suggestion.target_column,
                )
            except LlmError as exc:
                result.notes.append(
                    f"{suggestion.model}.{suggestion.column}: model unavailable "
                    f"({exc}); kept the rule result"
                )
                continue
            suggestion.status = STATUS_CONFIRMED if is_fk else STATUS_REJECTED
            if reason:
                suggestion.reasons.append(f"model: {reason}")

    result.bridges = _bridges(models, result.suggestions, declared, by_name)
    return result


def _column_of(by_name: dict[str, dict], model: str, column: str) -> dict:
    for col in by_name[model].get("columns") or []:
        if str(col.get("name")) == column:
            return col
    return {}


def _bridges(
    models: list[dict],
    suggestions: list[Suggestion],
    declared: dict[str, dict[str, str]],
    by_name: dict[str, dict],
) -> list[Bridge]:
    """Models whose every column is a foreign key to a different table.

    A column counts as a key when it is declared or accepted (suggested or
    confirmed). Rejected and ambiguous suggestions do not count.
    """
    mapping_by_model: dict[str, dict[str, str]] = {
        m: dict(cols) for m, cols in declared.items()
    }
    for s in suggestions:
        if s.status in (STATUS_SUGGESTED, STATUS_CONFIRMED):
            mapping_by_model.setdefault(s.model.lower(), {})[s.column.lower()] = (
                s.target_model.lower()
            )

    canonical = {name.lower(): name for name in by_name}
    bridges: list[Bridge] = []
    for model in models:
        mname = str(model["name"])
        columns = [str(c["name"]) for c in model.get("columns") or [] if c.get("name")]
        mapping = mapping_by_model.get(mname.lower(), {})
        if len(columns) < 2 or any(c.lower() not in mapping for c in columns):
            continue
        targets = sorted({mapping[c.lower()] for c in columns})
        if len(targets) < 2 or mname.lower() in targets:
            continue
        for a_low, b_low in _pairs(targets):
            a = canonical[a_low]
            b = canonical[b_low]
            col_a = next(c for c in columns if mapping[c.lower()] == a_low)
            col_b = next(c for c in columns if mapping[c.lower()] == b_low)
            key_a = _target_key(by_name, a)
            key_b = _target_key(by_name, b)
            join = (
                f"SELECT * FROM {a} a JOIN {mname} j ON j.{col_a} = a.{key_a} "
                f"JOIN {b} b ON j.{col_b} = b.{key_b}"
            )
            bridges.append(Bridge(mname, (a, b), (a, b), join))
    return bridges


def _target_key(by_name: dict[str, dict], model: str) -> str:
    lookup = {name.lower(): m for name, m in by_name.items()}
    return str((lookup.get(model) or {}).get("primary_key") or "")


def _pairs(items: list[str]) -> list[tuple[str, str]]:
    return [
        (items[i], items[j])
        for i in range(len(items))
        for j in range(i + 1, len(items))
    ]


# ── writing the draft ───────────────────────────────────────────────────────


def _relationship_name(s: Suggestion) -> str:
    return f"{s.model}_{s.target_model}_{s.column}"


def write_inference(project_path: Path, result: InferenceResult) -> dict[str, Any]:
    """Write ``draft/relationships.yml`` (accepted suggestions) and the detail files.

    Relationships are merged by name with any draft relationships already there.
    Returns a summary of what was written.
    """
    draft = project_path / "draft"
    draft.mkdir(parents=True, exist_ok=True)

    accepted = [
        s
        for s in result.suggestions
        if s.status in (STATUS_SUGGESTED, STATUS_CONFIRMED)
    ]
    new_rels = [
        {
            "name": _relationship_name(s),
            "models": [s.model, s.target_model],
            "join_type": "many_to_one",
            "condition": f"{s.model}.{s.column} = {s.target_model}.{s.target_column}",
        }
        for s in accepted
    ]

    rel_path = draft / RELATIONSHIPS_FILE
    existing: list[dict] = []
    if rel_path.exists():
        data = yaml.safe_load(rel_path.read_text(encoding="utf-8")) or {}
        existing = [r for r in data.get("relationships") or [] if isinstance(r, dict)]
    known = {r.get("name") for r in existing}
    merged = existing + [r for r in new_rels if r["name"] not in known]
    if merged:
        rel_path.write_text(
            yaml.safe_dump({"relationships": merged}, sort_keys=False), encoding="utf-8"
        )

    (draft / SUGGESTIONS_FILE).write_text(
        yaml.safe_dump(
            {
                "suggestions": [s.to_dict() for s in result.suggestions],
                "notes": result.notes,
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (draft / BRIDGES_FILE).write_text(
        yaml.safe_dump(
            {"bridges": [b.to_dict() for b in result.bridges]},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    counts: dict[str, int] = {}
    for s in result.suggestions:
        counts[s.status] = counts.get(s.status, 0) + 1
    return {
        "relationships_written": len(merged),
        "bridges": len(result.bridges),
        "by_status": counts,
    }
