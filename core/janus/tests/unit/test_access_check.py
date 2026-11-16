"""Access checks: spec validation and the verdict for each case."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from janus.access_check import (
    AccessCheckSpecError,
    Case,
    Result,
    load_cases,
    render_text,
    run_case,
)

pytestmark = pytest.mark.unit


def _plan_returning(text):
    return lambda sql, props: text


def _plan_raising(message):
    def plan(sql, props):
        raise RuntimeError(message)

    return plan


def _merge(props):
    return props


def _case(**kw):
    base = dict(name="c", sql="SELECT 1")
    base.update(kw)
    return Case(**base)


def test_contains_passes_when_the_plan_has_the_text():
    result = run_case(
        _case(contains=["= 'APAC'"]),
        _plan_returning("WHERE region = 'APAC'"),
        _merge,
    )
    assert result.passed


def test_contains_fails_when_the_text_is_missing():
    result = run_case(
        _case(contains=["= 'EU'"]),
        _plan_returning("WHERE region = 'APAC'"),
        _merge,
    )
    assert not result.passed
    assert "does not contain" in result.problems[0]


def test_not_contains_fails_when_the_text_is_present():
    result = run_case(
        _case(not_contains=["'EU'"]),
        _plan_returning("WHERE region = 'EU'"),
        _merge,
    )
    assert not result.passed


def test_expected_error_passes_when_the_message_matches():
    result = run_case(
        _case(error="required"),
        _plan_raising("session property x is required for rule y"),
        _merge,
    )
    assert result.passed


def test_expected_error_fails_when_planning_succeeds():
    result = run_case(_case(error="required"), _plan_returning("SELECT 1"), _merge)
    assert not result.passed
    assert "but planning succeeded" in result.problems[0]


def test_wrong_error_text_fails():
    result = run_case(
        _case(error="required"),
        _plan_raising("table not found"),
        _merge,
    )
    assert not result.passed


def test_unexpected_planning_failure_fails():
    result = run_case(_case(contains=["x"]), _plan_raising("boom"), _merge)
    assert not result.passed
    assert "planning failed" in result.problems[0]


@pytest.mark.parametrize(
    "leftover", ["WHERE amount > @min_amount", "WHERE amount > $min_amount"]
)
def test_unbound_placeholders_fail_even_when_contains_passes(leftover):
    result = run_case(_case(contains=["amount"]), _plan_returning(leftover), _merge)
    assert not result.passed
    assert "unbound placeholder" in result.problems[-1]


def test_a_dollar_inside_a_string_literal_is_not_a_placeholder():
    result = run_case(
        _case(contains=["'a'"]),
        _plan_returning("WHERE note = 'cost $5' AND x = 'a'"),
        _merge,
    )
    assert result.passed


def test_properties_reach_the_planner_through_merge():
    seen = {}

    def merge(props):
        seen.update(props)
        return {k: "'" + str(v) + "'" for k, v in props.items()}

    def plan(sql, props):
        seen["literal"] = props
        return "WHERE region = " + props["session_region"]

    result = run_case(
        _case(properties={"session_region": "APAC"}, contains=["'APAC'"]),
        plan,
        merge,
    )
    assert result.passed
    assert seen["literal"] == {"session_region": "'APAC'"}


def test_spec_loads_cases(tmp_path: Path):
    spec = tmp_path / "access_checks.yml"
    spec.write_text(
        yaml.safe_dump(
            {
                "cases": [
                    {
                        "name": "a",
                        "sql": "SELECT 1",
                        "properties": {"session_region": "APAC"},
                        "expect": {"contains": ["x"]},
                    },
                    {"sql": "SELECT 2", "expect": {"error": "required"}},
                ]
            }
        ),
        encoding="utf-8",
    )
    cases = load_cases(spec)
    assert cases[0].properties == {"session_region": "APAC"}
    assert cases[1].name == "case 2"
    assert cases[1].error == "required"


@pytest.mark.parametrize(
    "body, fragment",
    [
        ({}, '"cases" list'),
        ({"cases": []}, '"cases" list'),
        (
            {"cases": [{"name": "n", "expect": {"contains": ["x"]}}]},
            "needs a non-empty sql",
        ),
        (
            {"cases": [{"name": "n", "sql": "SELECT 1"}]},
            "needs contains, not_contains, or error",
        ),
        (
            {"cases": [{"name": "n", "sql": "S", "expect": {"contains": "x"}}]},
            "list of text",
        ),
        (
            {"cases": [{"name": "n", "sql": "S", "expect": {"error": 5}}]},
            "must be text",
        ),
        ({"cases": ["not a mapping"]}, "not a mapping"),
    ],
)
def test_bad_spec_is_rejected(tmp_path: Path, body, fragment):
    spec = tmp_path / "access_checks.yml"
    spec.write_text(yaml.safe_dump(body), encoding="utf-8")
    with pytest.raises(AccessCheckSpecError, match=fragment):
        load_cases(spec)


def test_render_text_reports_counts():
    text = render_text(
        [Result("ok", True), Result("bad", False, ["plan does not contain 'x'"])]
    )
    assert "PASS  ok" in text
    assert "FAIL  bad" in text
    assert text.endswith("1 passed, 1 failed")
