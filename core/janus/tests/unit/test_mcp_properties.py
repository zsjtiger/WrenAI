"""Session properties passed through the MCP query tools."""

from __future__ import annotations

import math

import pyarrow as pa
import pytest

from janus.mcp_server import (
    ServeContext,
    build_server,
    merge_properties,
    rls_property_names,
    to_sql_literal,
)
from janus.serve_cli import _parse_properties, _serve_args

pytestmark = pytest.mark.unit


class FakeEngine:
    """Records what the tools hand to the engine."""

    def __init__(self):
        self.calls: list[tuple] = []

    def query_with_provenance(self, sql, limit=None, properties=None):
        self.calls.append(("query", sql, properties))
        return pa.table({"x": [1]}), {}, sql

    def dry_run(self, sql, properties=None):
        self.calls.append(("dry_run", sql, properties))

    def dry_plan(self, sql, properties=None):
        self.calls.append(("dry_plan", sql, properties))
        return sql


def _ctx(tmp_path, engine=None, fixed=None, protected=frozenset()):
    return ServeContext(
        project=tmp_path,
        engine=engine or FakeEngine(),
        allow_write=False,
        no_connect=False,
        fixed_properties=fixed or {},
        protected_properties=frozenset(protected),
    )


def _tool(ctx, name):
    return build_server(ctx)._tool_manager._tools[name].fn


def test_string_values_are_quoted_and_escaped():
    assert to_sql_literal("APAC") == "'APAC'"
    assert to_sql_literal("O'Brien") == "'O''Brien'"


def test_numbers_and_booleans_are_plain_literals():
    assert to_sql_literal(2026) == "2026"
    assert to_sql_literal(1.5) == "1.5"
    assert to_sql_literal(True) == "TRUE"
    assert to_sql_literal(False) == "FALSE"


def test_non_finite_numbers_are_refused():
    with pytest.raises(ValueError):
        to_sql_literal(math.nan)


def test_rls_property_names_read_the_camel_case_mdl():
    mdl = {
        "models": [
            {
                "name": "customers",
                "rowLevelAccessControls": [
                    {
                        "name": "region_access",
                        "requiredProperties": [{"name": "session_region"}],
                        "condition": "region = @session_region",
                    }
                ],
            },
            {"name": "orders"},
        ]
    }
    assert rls_property_names(mdl) == frozenset({"session_region"})


def test_client_filter_reaches_the_engine_as_sql_literals(tmp_path):
    engine = FakeEngine()
    _tool(_ctx(tmp_path, engine), "run_sql")(
        "SELECT * FROM orders", properties={"year": 2026, "region": "APAC"}
    )
    kind, _, props = engine.calls[-1]
    assert kind == "query"
    assert props == {"year": "2026", "region": "'APAC'"}


def test_no_properties_means_none(tmp_path):
    engine = FakeEngine()
    _tool(_ctx(tmp_path, engine), "run_sql")("SELECT 1")
    assert engine.calls[-1][2] is None


def test_client_cannot_set_an_access_rule_property(tmp_path):
    engine = FakeEngine()
    run_sql = _tool(_ctx(tmp_path, engine, protected={"session_region"}), "run_sql")
    with pytest.raises(ValueError, match="set by the server"):
        run_sql("SELECT 1", properties={"session_region": "EU"})
    assert engine.calls == []


def test_server_fixed_value_is_used_and_cannot_be_overridden(tmp_path):
    engine = FakeEngine()
    ctx = _ctx(
        tmp_path,
        engine,
        fixed={"session_region": "APAC"},
        protected={"session_region"},
    )
    run_sql = _tool(ctx, "run_sql")
    run_sql("SELECT 1")
    assert engine.calls[-1][2] == {"session_region": "'APAC'"}
    with pytest.raises(ValueError, match="set by the server"):
        run_sql("SELECT 1", properties={"session_region": "EU"})


def test_invalid_property_names_are_refused(tmp_path):
    with pytest.raises(ValueError, match="invalid property name"):
        merge_properties(_ctx(tmp_path), {"a b": 1})


def test_dry_run_and_dry_plan_take_the_same_properties(tmp_path):
    engine = FakeEngine()
    ctx = _ctx(tmp_path, engine)
    _tool(ctx, "dry_plan")("SELECT 1", properties={"year": 2026})
    _tool(ctx, "dry_run")("SELECT 1", properties={"year": 2026})
    assert engine.calls[0] == ("dry_plan", "SELECT 1", {"year": "2026"})
    assert engine.calls[1] == ("dry_run", "SELECT 1", {"year": "2026"})


def test_property_options_parse_to_name_value_pairs():

    assert _parse_properties(["session_region=APAC", "year=2026"]) == {
        "session_region": "APAC",
        "year": "2026",
    }
    with pytest.raises(Exception, match="name=value"):
        _parse_properties(["no-equals-sign"])


def test_registration_command_carries_the_fixed_properties(tmp_path):
    args = _serve_args(tmp_path, None, False, False, ["session_region=APAC"])
    assert args[-2:] == ["--property", "session_region=APAC"]
