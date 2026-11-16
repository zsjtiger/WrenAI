"""Access code paths the other tests do not reach: config errors, legacy requests,
literal and audit edge cases, stdio roles, and the access CLI."""

from __future__ import annotations

import base64
import json

import pyarrow as pa
import pytest
import typer
import yaml
from starlette.testclient import TestClient
from typer.testing import CliRunner

import janus.profile as profile_module
from janus.access import (
    AccessConfigError,
    AccessError,
    Audit,
    Check,
    build_runtime,
    collect_rules,
    cross_check,
    evaluate_roles,
    find_token,
    format_report,
    load_access_config,
    parse_access_config,
    prepare_call,
    resolve,
    sql_literal,
    write_audit,
    write_refusal,
)
from janus.api_server import build_app, run_api
from janus.cli import app as main_app
from janus.mcp_server import ServeContext, _presented_token, build_server
from janus.model.error import ErrorCode, JanusError
from janus.serve_cli import _build_access, _parse_properties, _property_value
from tests.unit.conftest import manifest_b64, model_dict

pytestmark = pytest.mark.unit

ENV = {"TOK_A": "a-secret", "TOK_B": "b-secret"}


def _base():
    return {
        "version": 1,
        "roles": {
            "analyst": {
                "sql": "SELECT 1 AS session_level, 1 AS session_customer",
                "allow_override": ["session_customer"],
            },
            "manager": {"sql": "SELECT 3 AS session_level, 0 AS session_customer"},
        },
        "tokens": [
            {
                "id": "a",
                "token_env": "TOK_A",
                "default_role": "analyst",
                "may_override": True,
            },
            {
                "id": "b",
                "token_env": "TOK_B",
                "default_role": "manager",
                "may_request_role": True,
            },
        ],
    }


def _mdl():
    return {
        "models": [
            {
                "name": "orders",
                "columns": [
                    {"name": "order_id"},
                    {
                        "name": "amount",
                        "columnLevelAccessControl": {
                            "name": "amt",
                            "requiredProperties": [
                                {"name": "session_level", "required": True}
                            ],
                            "operator": "GREATER_THAN_OR_EQUALS",
                            "threshold": "2",
                        },
                    },
                ],
                "rowLevelAccessControls": [
                    {
                        "name": "own",
                        "requiredProperties": [
                            {"name": "session_customer", "required": True}
                        ],
                        "condition": "customer_id = @session_customer",
                    }
                ],
            }
        ]
    }


def _values():
    return {
        "analyst": {"session_level": 1, "session_customer": 1},
        "manager": {"session_level": 3, "session_customer": 0},
    }


# ── config parsing errors ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda b: b.update(roles=[]), "roles"),
        (lambda b: b.update(roles={}), "roles must not be empty"),
        (
            lambda b: b["roles"].update({"9bad": {"sql": "SELECT 1 AS a"}}),
            "not a valid identifier",
        ),
        (
            lambda b: b["roles"]["analyst"].update(allow_override="session_customer"),
            "list of names",
        ),
        (lambda b: b["roles"]["analyst"].update(sql=5), "non-empty string"),
        (lambda b: b.update(tokens=[]), "non-empty list"),
        (lambda b: b.update(tokens=["x"]), "must be a mapping"),
        (lambda b: b["tokens"][0].update(bogus=1), "unknown field"),
        (lambda b: b["tokens"][0].update(id=""), "non-empty string"),
        (lambda b: b["tokens"][0].update(token_env=""), "token_env is required"),
        (lambda b: b.update(audit={"path": "x", "nope": 1}), "unknown field"),
        (lambda b: b.update(audit="x"), "audit must be a mapping"),
    ],
)
def test_config_errors_are_reported(mutate, fragment):
    body = _base()
    mutate(body)
    with pytest.raises(AccessConfigError, match=fragment):
        parse_access_config(body, ENV)


def test_a_non_mapping_config_is_refused():
    with pytest.raises(AccessConfigError, match="must be a mapping"):
        parse_access_config(["not", "a", "mapping"], ENV)


def test_an_unreadable_config_file_is_refused(tmp_path):
    with pytest.raises(AccessConfigError, match="cannot read"):
        load_access_config(tmp_path / "missing.yml", ENV)


def test_invalid_yaml_is_refused(tmp_path):
    path = tmp_path / "bad.yml"
    path.write_text("roles: [unclosed", encoding="utf-8")
    with pytest.raises(AccessConfigError, match="cannot read"):
        load_access_config(path, ENV)


def test_an_audit_path_is_optional():
    cfg = parse_access_config(_base(), ENV)
    assert cfg.audit.path is None and cfg.audit.record_sql is True


# ── roles and cross-check ───────────────────────────────────────────────────


def test_evaluate_roles_refuses_an_invalid_column_name():
    cfg = parse_access_config(_base(), ENV)
    with pytest.raises(AccessConfigError, match="not a valid name"):
        evaluate_roles(cfg, lambda sql: [{"bad-name": 1}])


def test_a_threshold_that_is_not_a_number_is_an_error():
    mdl = _mdl()
    mdl["models"][0]["columns"][1]["columnLevelAccessControl"]["threshold"] = "high"
    cfg = parse_access_config(_base(), ENV)
    check = cross_check(cfg, mdl, _values())
    assert any("is not a number" in e for e in check.errors)


def test_an_unknown_operator_is_an_error():
    mdl = _mdl()
    mdl["models"][0]["columns"][1]["columnLevelAccessControl"]["operator"] = "BETWEEN"
    cfg = parse_access_config(_base(), ENV)
    check = cross_check(cfg, mdl, _values())
    assert any("unknown operator" in e for e in check.errors)


def test_a_fixed_property_is_warned_as_overriding_the_role():
    cfg = parse_access_config(_base(), ENV)
    check = cross_check(cfg, _mdl(), _values(), fixed={"session_level": 2})
    assert any("fixed by --property" in w for w in check.warnings)


def test_a_fixed_property_covers_a_missing_role_value():
    cfg = parse_access_config(_base(), ENV)
    values = _values()
    del values["manager"]["session_level"]
    check = cross_check(cfg, _mdl(), values, fixed={"session_level": 3})
    assert not any("manager" in w and "session_level" in w for w in check.warnings)


def test_a_column_rule_on_a_missing_value_reports_no_value_in_the_report():
    cfg = parse_access_config(_base(), ENV)
    values = _values()
    del values["analyst"]["session_level"]
    check = cross_check(cfg, _mdl(), values)
    text = format_report(check)
    assert "denied: amount (no session_level)" in text


def test_a_non_comparable_value_is_reported_not_raised():
    cfg = parse_access_config(_base(), ENV)
    values = _values()
    values["analyst"]["session_level"] = "high"
    check = cross_check(cfg, _mdl(), values)
    report = next(r for r in check.report if r["role"] == "analyst")
    assert any("is not comparable" in d for d in report["columns_denied"])


def test_format_report_lists_warnings_and_errors():
    check = Check(errors=["bad thing"], warnings=["odd thing"])
    text = format_report(check)
    assert "warning: odd thing" in text and "error: bad thing" in text


def test_build_runtime_refuses_on_errors():
    cfg = parse_access_config(_base(), ENV)
    mdl = _mdl()
    mdl["models"][0]["rowLevelAccessControls"][0]["requiredProperties"][0][
        "required"
    ] = False
    rows = {
        "analyst": [{"session_level": 1, "session_customer": 1}],
        "manager": [{"session_level": 3, "session_customer": 0}],
    }
    with pytest.raises(AccessConfigError, match="optional"):
        build_runtime(cfg, mdl, lambda sql: rows[_role_for(cfg, sql)])


def _role_for(cfg, sql):
    return next(name for name, role in cfg.roles.items() if role.sql == sql)


def test_collect_rules_reads_the_camel_case_manifest():
    rows, cols = collect_rules(_mdl())
    assert rows[0].condition.startswith("customer_id")
    assert cols[0].operator == "GREATER_THAN_OR_EQUALS"


# ── literals and the legacy (no access config) path ─────────────────────────


def test_sql_literal_refuses_unsupported_types_and_non_finite_numbers():
    with pytest.raises(AccessError):
        sql_literal(float("inf"))
    with pytest.raises(AccessError):
        sql_literal([1, 2])


def test_sql_literal_writes_booleans():
    assert sql_literal(True) == "TRUE"
    assert sql_literal(False) == "FALSE"


def test_legacy_requests_need_a_trusted_caller_for_properties():
    with pytest.raises(AccessError) as exc:
        prepare_call(
            runtime=None,
            fixed={},
            trusted=False,
            presented=None,
            request_props={"session_customer": 1},
        )
    assert exc.value.code == "override_forbidden"


def test_legacy_requests_cannot_choose_a_role():
    with pytest.raises(AccessError) as exc:
        prepare_call(
            runtime=None, fixed={}, trusted=True, presented="x", request_role="manager"
        )
    assert exc.value.code == "role_not_allowed"


def test_legacy_fixed_values_cannot_be_overridden():
    with pytest.raises(AccessError) as exc:
        prepare_call(
            runtime=None,
            fixed={"session_level": 3},
            trusted=True,
            presented="x",
            request_props={"session_level": 1},
        )
    assert exc.value.code == "fixed_property"


def test_legacy_trusted_request_uses_its_properties_and_the_fixed_ones():
    resolved = prepare_call(
        runtime=None,
        fixed={"tenant": "eu"},
        trusted=True,
        presented="x",
        request_props={"session_customer": 2},
    )
    assert resolved.literals == {"session_customer": "2", "tenant": "'eu'"}
    assert resolved.sources == {"session_customer": "request", "tenant": "fixed"}
    assert resolved.role is None


def test_no_properties_gives_no_literals():
    resolved = prepare_call(runtime=None, fixed={}, trusted=False, presented=None)
    assert resolved.literals is None


# ── resolution details ──────────────────────────────────────────────────────


def test_find_token_returns_none_without_a_presented_token():
    cfg = parse_access_config(_base(), ENV)
    assert find_token(cfg, None) is None
    assert find_token(cfg, "") is None


def test_a_stdio_role_that_does_not_exist_is_refused():
    cfg = parse_access_config(_base(), ENV)
    with pytest.raises(AccessError) as exc:
        resolve(cfg, _values(), None, token=None, stdio_role="ghost")
    assert exc.value.code == "unknown_role"


def test_a_fixed_value_is_recorded_with_its_source():
    cfg = parse_access_config(_base(), ENV)
    resolved = resolve(
        cfg, _values(), {"session_customer": 9}, token=find_token(cfg, "a-secret")
    )
    assert resolved.values["session_customer"] == 9
    assert resolved.sources["session_customer"] == "fixed"


# ── audit ───────────────────────────────────────────────────────────────────


def test_audit_is_a_noop_without_a_path():
    cfg = parse_access_config(_base(), ENV)
    resolved = resolve(cfg, _values(), None, token=find_token(cfg, "a-secret"))
    write_audit(Audit(path=None), resolved, sql="SELECT 1", status="ok")
    write_refusal(
        Audit(path=None), "a", sql="SELECT 1", error=AccessError("x", "y", 403)
    )


def test_a_refusal_is_written_without_sql_when_sql_is_not_recorded(tmp_path):
    path = tmp_path / "audit.jsonl"
    write_refusal(
        Audit(path=path, record_sql=False),
        "svc",
        sql="SELECT 1",
        error=AccessError("override_forbidden", "no", 403),
    )
    entry = json.loads(path.read_text())
    assert entry["status"] == "denied" and entry["code"] == "override_forbidden"
    assert "sql" not in entry


# ── the access CLI, end to end on a DuckDB profile ─────────────────────────


@pytest.fixture
def cli_env(tmp_path, monkeypatch, make_project, shop_dir):

    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        yaml.safe_dump(
            {
                "active": "demo",
                "profiles": {
                    "demo": {
                        "datasource": "duckdb",
                        "url": str(shop_dir),
                        "format": "duckdb",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(profile_module, "_PROFILES_FILE", profiles)
    monkeypatch.setenv("TOK_A", "a-secret")
    monkeypatch.setenv("TOK_B", "b-secret")
    customers = model_dict(
        "customers",
        "customers",
        [("id", "INTEGER"), ("name", "VARCHAR")],
        primary_key="id",
    )
    customers["rowLevelAccessControls"] = [
        {
            "name": "own_row",
            "requiredProperties": [{"name": "session_level", "required": True}],
            "condition": "id <= @session_level",
        }
    ]
    project = make_project([customers])

    return CliRunner(), project


def _config(tmp_path, *, rule_required=True):
    body = {
        "version": 1,
        "roles": {"reader": {"sql": "SELECT 1 AS session_level"}},
        "tokens": [{"id": "a", "token_env": "TOK_A", "default_role": "reader"}],
    }
    path = tmp_path / "access.yml"
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


def test_access_report_needs_the_config_flag(cli_env):
    runner, project = cli_env
    result = runner.invoke(main_app, ["access", "report", "--path", str(project)])
    assert result.exit_code == 2
    assert "--access-config" in result.output


def test_access_report_needs_a_built_project(cli_env, tmp_path):
    runner, project = cli_env
    cfg = _config(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(
        main_app,
        ["access", "report", "--path", str(empty), "--access-config", str(cfg)],
    )
    assert result.exit_code == 2
    assert "janus context build" in result.output


def test_access_report_refuses_an_invalid_config(cli_env, tmp_path):
    runner, project = cli_env
    _build(project)
    bad = tmp_path / "bad.yml"
    bad.write_text("version: 2\n", encoding="utf-8")
    result = runner.invoke(
        main_app,
        ["access", "report", "--path", str(project), "--access-config", str(bad)],
    )
    assert result.exit_code == 2
    assert "access config" in result.output


def test_access_report_prints_each_role_on_a_good_config(cli_env, tmp_path):

    runner, project = cli_env
    _build(project)
    cfg = _config(tmp_path)
    result = runner.invoke(
        main_app,
        [
            "access",
            "report",
            "--path",
            str(project),
            "--access-config",
            str(cfg),
            "--profile",
            "demo",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "role reader" in result.output
    assert "ok: no errors or warnings" in result.output


def test_access_report_json_output(cli_env, tmp_path):
    runner, project = cli_env
    _build(project)
    cfg = _config(tmp_path)
    result = runner.invoke(
        main_app,
        [
            "access",
            "report",
            "--path",
            str(project),
            "--access-config",
            str(cfg),
            "--json",
            "--profile",
            "demo",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["errors"] == []
    assert payload["report"][0]["role"] == "reader"


def test_access_report_exits_one_on_a_rule_error(cli_env, tmp_path):
    runner, project = cli_env
    _build(project, optional_rule=True)
    cfg = _config(tmp_path)
    result = runner.invoke(
        main_app,
        [
            "access",
            "report",
            "--path",
            str(project),
            "--access-config",
            str(cfg),
            "--profile",
            "demo",
        ],
    )
    assert result.exit_code == 1
    assert "optional" in result.output


def _build(project, *, optional_rule=False):
    """Compile the project's target/mdl.json, with an access rule on customers if asked."""

    target = project / "target"
    target.mkdir(exist_ok=True)
    mdl = json.loads(base64.b64decode(_manifest(project)))
    if optional_rule:
        mdl["models"][0]["rowLevelAccessControls"] = [
            {
                "name": "own",
                "requiredProperties": [{"name": "session_customer", "required": False}],
                "condition": "id = @session_customer",
            }
        ]
    (target / "mdl.json").write_text(json.dumps(mdl), encoding="utf-8")


def _manifest(project):

    return manifest_b64(project)


# ── serve_cli helpers ───────────────────────────────────────────────────────


def test_property_values_keep_numbers_and_text():

    assert _property_value("7") == 7
    assert _property_value("2.5") == 2.5
    assert _property_value("-3") == -3
    assert _property_value("007") == "007"
    assert _property_value("APAC") == "APAC"
    assert _parse_properties(["a=1", "b=x=y"]) == {"a": 1, "b": "x=y"}


def test_a_property_without_equals_is_a_bad_parameter():

    with pytest.raises(typer.BadParameter):
        _parse_properties(["noequals"])
    with pytest.raises(typer.BadParameter):
        _parse_properties(["=value"])


def test_build_access_without_a_config_is_none(tmp_path):

    assert _build_access(None, {}, tmp_path / "mdl.json", None) is None


def test_build_access_exits_two_on_an_invalid_config(tmp_path):

    bad = tmp_path / "bad.yml"
    bad.write_text("version: 2\n", encoding="utf-8")
    with pytest.raises(typer.Exit) as exc:
        _build_access(str(bad), {}, tmp_path / "mdl.json", None)
    assert exc.value.exit_code == 2


# ── the stdio --role path ───────────────────────────────────────────────────


class _Recorder:
    def __init__(self):
        self.calls = []

    def query_with_provenance(self, sql, limit=None, properties=None):
        self.calls.append(properties)
        return pa.table({"x": [1]}), {}, sql

    def dry_plan(self, sql, properties=None):
        self.calls.append(properties)
        return sql

    def dry_run(self, sql, properties=None):
        self.calls.append(properties)


def test_stdio_role_sets_the_values_and_refuses_overrides(tmp_path):

    cfg = parse_access_config(_base(), ENV)
    rows = {
        "analyst": [{"session_level": 1, "session_customer": 1}],
        "manager": [{"session_level": 3, "session_customer": 0}],
    }
    runtime = build_runtime(cfg, {"models": []}, lambda sql: rows[_role_for(cfg, sql)])
    engine = _Recorder()
    ctx = ServeContext(
        project=tmp_path,
        engine=engine,
        allow_write=False,
        no_connect=False,
        access=runtime,
        stdio_role="manager",
    )
    run_sql = build_server(ctx)._tool_manager._tools["run_sql"].fn
    run_sql("SELECT 1")
    assert engine.calls[-1] == {"session_level": "3", "session_customer": "0"}
    with pytest.raises(ValueError, match="override_forbidden"):
        run_sql("SELECT 1", properties={"session_customer": 5})


def test_a_refused_mcp_call_is_audited(tmp_path):

    body = _base()
    body["audit"] = {"path": str(tmp_path / "audit.jsonl"), "record_sql": True}
    cfg = parse_access_config(body, ENV)
    rows = {
        "analyst": [{"session_level": 1, "session_customer": 1}],
        "manager": [{"session_level": 3, "session_customer": 0}],
    }
    runtime = build_runtime(cfg, {"models": []}, lambda sql: rows[_role_for(cfg, sql)])
    ctx = ServeContext(
        project=tmp_path,
        engine=_Recorder(),
        allow_write=False,
        no_connect=False,
        access=runtime,
        stdio_role="analyst",
    )
    dry_run = build_server(ctx)._tool_manager._tools["dry_run"].fn
    with pytest.raises(ValueError, match="role_not_allowed"):
        dry_run("SELECT 1", role="manager")
    entry = json.loads((tmp_path / "audit.jsonl").read_text().splitlines()[-1])
    assert entry["status"] == "denied" and entry["code"] == "role_not_allowed"


# ── HTTP legacy (no access config) ──────────────────────────────────────────


def test_http_legacy_token_guard_and_trust(tmp_path):

    engine = _Recorder()
    ctx = ServeContext(
        project=tmp_path, engine=engine, allow_write=False, no_connect=False
    )
    client = TestClient(build_app(ctx, token="s3cret"))
    assert client.post("/dry-plan", json={"sql": "SELECT 1"}).status_code == 401
    ok = client.post(
        "/dry-plan",
        json={"sql": "SELECT 1"},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert ok.status_code == 200
    refused = client.post("/dry-plan", json={"sql": "SELECT 1", "properties": {"x": 1}})
    assert refused.status_code == 401
    trusted = client.post(
        "/dry-plan",
        json={"sql": "SELECT 1", "properties": {"x": 1}},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert trusted.status_code == 200


def test_http_legacy_properties_need_a_token_or_the_flag(tmp_path):

    ctx = ServeContext(
        project=tmp_path, engine=_Recorder(), allow_write=False, no_connect=False
    )
    client = TestClient(build_app(ctx, token=None))
    r = client.post("/dry-plan", json={"sql": "SELECT 1", "properties": {"x": 1}})
    assert r.status_code == 403 and r.json()["code"] == "override_forbidden"


def test_http_body_validation_for_role_and_properties(tmp_path):

    ctx = ServeContext(
        project=tmp_path,
        engine=_Recorder(),
        allow_write=False,
        no_connect=False,
        trust_client_properties=True,
    )
    client = TestClient(build_app(ctx, token=None))
    assert (
        client.post("/dry-plan", json={"sql": "SELECT 1", "role": 5}).status_code == 400
    )
    assert (
        client.post(
            "/dry-plan", json={"sql": "SELECT 1", "properties": "x"}
        ).status_code
        == 400
    )
    assert (
        client.post("/dry-plan", json={"sql": "SELECT 1", "role": "x"}).status_code
        == 403
    )


def test_a_non_loopback_api_without_a_token_or_config_is_refused(tmp_path):

    ctx = ServeContext(
        project=tmp_path, engine=_Recorder(), allow_write=False, no_connect=False
    )
    with pytest.raises(ValueError, match="without a token"):
        run_api(ctx, host="0.0.0.0", port=1, token=None)


# ── more access paths: audited query errors, dry-run success, serve validation ──


def _access_app(tmp_path, *, audit=True):
    """A runtime over a stand-in engine, with the audit file under tmp_path."""
    body = _base()
    if audit:
        body["audit"] = {"path": str(tmp_path / "audit.jsonl"), "record_sql": True}
    cfg = parse_access_config(body, ENV)
    rows = {
        "analyst": [{"session_level": 1, "session_customer": 1}],
        "manager": [{"session_level": 3, "session_customer": 0}],
    }
    return build_runtime(cfg, {"models": []}, lambda sql: rows[_role_for(cfg, sql)])


def test_http_query_errors_are_audited(tmp_path):

    class Failing(_Recorder):
        def query_with_provenance(self, sql, limit=None, properties=None):
            raise JanusError(ErrorCode.GENERIC_USER_ERROR, "boom")

    ctx = ServeContext(
        project=tmp_path,
        engine=Failing(),
        allow_write=False,
        no_connect=False,
        access=_access_app(tmp_path),
    )
    client = TestClient(build_app(ctx, token=None))
    token = {"Authorization": "Bearer analyst-secret"}
    ENV_TOKEN = "a-secret"  # the config maps this value to the analyst token
    assert ENV_TOKEN
    r = client.post(
        "/query", json={"sql": "SELECT 1"}, headers={"Authorization": "Bearer a-secret"}
    )
    assert r.status_code == 422
    bad_limit = client.post(
        "/query",
        json={"sql": "SELECT 1", "limit": -1},
        headers={"Authorization": "Bearer a-secret"},
    )
    assert bad_limit.status_code == 400
    lines = [json.loads(x) for x in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert [line["status"] for line in lines] == ["error", "error"]
    assert "boom" in lines[0]["error"]
    assert token


def test_mcp_dry_run_succeeds_with_a_role(tmp_path):

    engine = _Recorder()
    ctx = ServeContext(
        project=tmp_path,
        engine=engine,
        allow_write=False,
        no_connect=False,
        access=_access_app(tmp_path),
        stdio_role="manager",
    )
    dry_run = build_server(ctx)._tool_manager._tools["dry_run"].fn
    assert dry_run("SELECT 1") == {"ok": True}
    assert engine.calls[-1] == {"session_level": "3", "session_customer": "0"}


def test_presented_token_is_none_without_a_request():

    class Context:
        request_context = type("RC", (), {"request": None})()

    assert _presented_token(Context()) is None


def test_presented_token_reads_the_bearer_header():

    class Request:
        headers = {"authorization": "Bearer abc"}

    class Context:
        request_context = type("RC", (), {"request": Request()})()

    assert _presented_token(Context()) == "abc"


def _serve_project(tmp_path, monkeypatch, shop_dir):
    """A built project plus a DuckDB profile, so `serve mcp --profile demo` can start."""
    profiles = tmp_path / "profiles.yml"
    profiles.write_text(
        yaml.safe_dump(
            {
                "active": "demo",
                "profiles": {
                    "demo": {
                        "datasource": "duckdb",
                        "url": str(shop_dir),
                        "format": "duckdb",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(profile_module, "_PROFILES_FILE", profiles)
    project = tmp_path / "project"
    (project / "target").mkdir(parents=True)
    (project / "target" / "mdl.json").write_text(
        json.dumps(
            {
                "catalog": "c",
                "schema": "s",
                "models": [],
                "views": [],
                "relationships": [],
            }
        ),
        encoding="utf-8",
    )
    return project


def _base_with_env():
    return _base()


def test_serve_mcp_refuses_an_unknown_stdio_role(tmp_path, monkeypatch, shop_dir):
    project = _serve_project(tmp_path, monkeypatch, shop_dir)
    cfg = tmp_path / "access.yml"
    cfg.write_text(yaml.safe_dump(_base()), encoding="utf-8")
    result = CliRunner().invoke(
        main_app,
        [
            "serve",
            "mcp",
            "--project",
            str(project),
            "--profile",
            "demo",
            "--no-connect",
            "--quiet",
            "--access-config",
            str(cfg),
            "--role",
            "ghost",
        ],
        env=ENV,
    )
    assert result.exit_code == 2, result.output
    assert "is not a role" in result.output


def test_serve_mcp_refuses_a_role_without_a_config(tmp_path, monkeypatch, shop_dir):
    project = _serve_project(tmp_path, monkeypatch, shop_dir)
    result = CliRunner().invoke(
        main_app,
        [
            "serve",
            "mcp",
            "--project",
            str(project),
            "--profile",
            "demo",
            "--no-connect",
            "--quiet",
            "--role",
            "x",
        ],
    )
    assert result.exit_code == 2, result.output
    assert "needs --access-config" in result.output
