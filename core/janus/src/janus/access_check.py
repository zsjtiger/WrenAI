"""Check row-level access rules by planning SQL under given identities.

A spec file (``access_checks.yml`` in the project) lists cases. Each case names
an identity (session ``properties``), a query, and what the planned SQL must do:

.. code-block:: yaml

    cases:
      - name: APAC customer 7 is filtered to their own rows
        sql: SELECT customer_id FROM customers
        properties: {session_customer: 7}
        expect:
          contains: ["customers.customer_id = 7"]
      - name: no identity is refused
        sql: SELECT customer_id FROM customers
        expect:
          error: "required"

Planning needs no database. The checks run as the project owner, so a case may
set access-rule properties. Every planned SQL is also checked for leftover
``@name`` or ``$name`` placeholders, which would mean a value was not bound.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ACCESS_CHECKS_FILE = "access_checks.yml"
_PLACEHOLDER = re.compile(r"(?<![\w.])[@$][A-Za-z_][A-Za-z0-9_]*")


class AccessCheckSpecError(ValueError):
    """The spec file is missing a required field or has the wrong shape."""


@dataclass
class Case:
    name: str
    sql: str
    properties: dict[str, Any] = field(default_factory=dict)
    contains: list[str] = field(default_factory=list)
    not_contains: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class Result:
    name: str
    passed: bool
    problems: list[str] = field(default_factory=list)
    planned: str | None = None


def load_cases(spec_path: Path) -> list[Case]:
    """Read and validate the spec file."""
    try:
        data = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise AccessCheckSpecError(f"cannot read {spec_path}: {exc}") from exc
    raw_cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(raw_cases, list) or not raw_cases:
        raise AccessCheckSpecError('spec needs a non-empty "cases" list')
    return [_case(i, raw) for i, raw in enumerate(raw_cases, start=1)]


def _case(index: int, raw: Any) -> Case:
    if not isinstance(raw, dict):
        raise AccessCheckSpecError(f"case {index} is not a mapping")
    name = str(raw.get("name") or f"case {index}")
    sql = raw.get("sql")
    if not isinstance(sql, str) or not sql.strip():
        raise AccessCheckSpecError(f"{name}: needs a non-empty sql")
    props = raw.get("properties") or {}
    if not isinstance(props, dict):
        raise AccessCheckSpecError(f"{name}: properties must be a mapping")
    expect = raw.get("expect") or {}
    if not isinstance(expect, dict):
        raise AccessCheckSpecError(f"{name}: expect must be a mapping")
    contains = _strings(expect.get("contains"), name, "contains")
    not_contains = _strings(expect.get("not_contains"), name, "not_contains")
    error = expect.get("error")
    if error is not None and not isinstance(error, str):
        raise AccessCheckSpecError(f"{name}: expect.error must be text")
    if error is None and not contains and not not_contains:
        raise AccessCheckSpecError(
            f"{name}: expect needs contains, not_contains, or error"
        )
    return Case(name, sql, dict(props), contains, not_contains, error)


def _strings(value: Any, name: str, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise AccessCheckSpecError(f"{name}: expect.{key} must be a list of text")
    return list(value)


def run_case(case: Case, plan: Any, merge: Any) -> Result:
    """Plan one case and compare the result with its expectations.

    ``plan(sql, properties)`` returns the planned SQL, or raises. ``merge``
    turns the case's properties into the engine's literal form.
    """
    result = Result(case.name, passed=True)
    try:
        planned = plan(case.sql, merge(case.properties))
    except Exception as exc:  # noqa: BLE001 - the planner's message is the result
        message = str(exc)
        if case.error is None:
            result.problems.append(f"planning failed: {message[:200]}")
        elif case.error not in message:
            result.problems.append(
                f"expected error containing {case.error!r}, got: {message[:200]}"
            )
        result.passed = not result.problems
        return result

    result.planned = planned
    if case.error is not None:
        result.problems.append(
            f"expected an error containing {case.error!r}, but planning succeeded"
        )
    for needle in case.contains:
        if needle not in planned:
            result.problems.append(f"plan does not contain {needle!r}")
    for needle in case.not_contains:
        if needle in planned:
            result.problems.append(f"plan contains {needle!r}")
    leftover = sorted(set(_PLACEHOLDER.findall(planned)))
    if leftover:
        result.problems.append(f"unbound placeholder(s) in plan: {', '.join(leftover)}")
    result.passed = not result.problems
    return result


def run_checks(cases: list[Case], plan: Any, merge: Any) -> list[Result]:
    return [run_case(case, plan, merge) for case in cases]


def render_text(results: list[Result]) -> str:
    lines = []
    for r in results:
        lines.append(f"{'PASS' if r.passed else 'FAIL'}  {r.name}")
        for problem in r.problems:
            lines.append(f"      - {problem}")
    failed = sum(1 for r in results if not r.passed)
    lines.append("")
    lines.append(f"{len(results) - failed} passed, {failed} failed")
    return "\n".join(lines)


def to_json(results: list[Result]) -> list[dict[str, Any]]:
    return [
        {
            "name": r.name,
            "passed": r.passed,
            "problems": r.problems,
            "planned": r.planned,
        }
        for r in results
    ]
