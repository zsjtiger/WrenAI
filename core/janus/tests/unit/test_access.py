"""Role-based access: config validation, cross-check with the model, and resolution."""

from __future__ import annotations

import json

import pytest
import yaml

from janus.access import (
    AccessConfigError,
    AccessError,
    Audit,
    cross_check,
    evaluate_roles,
    find_token,
    format_report,
    load_access_config,
    parse_access_config,
    resolve,
    sql_literal,
    write_audit,
)

pytestmark = pytest.mark.unit

ENV = {"TOK_SHOP": "shop-secret", "TOK_BI": "bi-secret"}


def _config(**overrides):
    body = {
        "version": 1,
        "roles": {
            "analyst": {
                "sql": "SELECT 1 AS session_level, 'c_001' AS session_customer",
                "allow_override": ["session_customer"],
            },
            "manager": {
                "sql": "SELECT 3 AS session_level, 'ALL' AS session_customer",
                "allow_override": [],
            },
        },
        "tokens": [
            {
                "id": "svc_shop",
                "token_env": "TOK_SHOP",
                "default_role": "analyst",
                "may_request_role": False,
                "may_override": True,
            },
            {
                "id": "svc_bi",
                "token_env": "TOK_BI",
                "default_role": "manager",
                "may_request_role": True,
                "may_override": False,
            },
        ],
    }
    body.update(overrides)
    return body


def _mdl():
    return {
        "models": [
            {
                "name": "orders",
                "columns": [
                    {"name": "order_id"},
                    {"name": "customer_id"},
                    {
                        "name": "amount",
                        "columnLevelAccessControl": {
                            "name": "amount_for_managers",
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
                        "name": "own_orders",
                        "requiredProperties": [
                            {"name": "session_customer", "required": True}
                        ],
                        "condition": "customer_id = @session_customer",
                    }
                ],
            }
        ]
    }


def _values(config):
    rows = {
        "analyst": [{"session_level": 1, "session_customer": "c_001"}],
        "manager": [{"session_level": 3, "session_customer": "ALL"}],
    }
    return evaluate_roles(config, lambda sql: rows[sql_role(config, sql)])


def sql_role(config, sql):
    for name, role in config.roles.items():
        if role.sql == sql:
            return name
    raise AssertionError(sql)


def _config_obj(**overrides):
    return parse_access_config(_config(**overrides), ENV)


# ── loading and validation ──────────────────────────────────────────────────


def test_a_valid_config_loads_roles_and_tokens():
    cfg = _config_obj()
    assert set(cfg.roles) == {"analyst", "manager"}
    assert cfg.tokens[0].value == "shop-secret"
    assert cfg.tokens[1].may_request_role is True


def test_yaml_text_loads_too(tmp_path):
    path = tmp_path / "janus_access.yml"
    path.write_text(yaml.safe_dump(_config()), encoding="utf-8")
    assert set(load_access_config(path, ENV).roles) == {"analyst", "manager"}


def test_unknown_top_level_field_is_refused():
    with pytest.raises(AccessConfigError, match="unknown field"):
        _config_obj(surprise=1)


def test_unknown_role_field_is_refused():
    body = _config()
    body["roles"]["analyst"]["sq1"] = "typo"
    with pytest.raises(AccessConfigError, match="unknown field"):
        parse_access_config(body, ENV)


def test_wrong_version_is_refused():
    with pytest.raises(AccessConfigError, match="version"):
        _config_obj(version=2)


@pytest.mark.parametrize(
    "sql",
    ["SELECT 1; DROP TABLE x", "SELECT 1\nFROM t", "DELETE FROM t", ""],
)
def test_role_sql_must_be_one_single_line_select(sql):
    body = _config()
    body["roles"]["analyst"]["sql"] = sql
    with pytest.raises(AccessConfigError):
        parse_access_config(body, ENV)


def test_a_missing_token_variable_is_refused():
    with pytest.raises(AccessConfigError, match="TOK_SHOP"):
        parse_access_config(_config(), {})


def test_default_role_must_exist():
    body = _config()
    body["tokens"][0]["default_role"] = "nobody"
    with pytest.raises(AccessConfigError, match="default_role"):
        parse_access_config(body, ENV)


def test_duplicate_token_ids_are_refused():
    body = _config()
    body["tokens"][1]["id"] = "svc_shop"
    with pytest.raises(AccessConfigError, match="duplicate"):
        parse_access_config(body, ENV)


def test_a_role_sql_must_return_one_row():
    cfg = _config_obj()
    with pytest.raises(AccessConfigError, match="one row"):
        evaluate_roles(cfg, lambda sql: [])


def test_allow_override_must_be_a_result_column():
    cfg = _config_obj()
    cfg.roles["analyst"].allow_override = ["not_a_column"]
    with pytest.raises(AccessConfigError, match="not a result column"):
        evaluate_roles(cfg, lambda sql: [{"session_customer": "c_001"}])


# ── cross-check with the model ──────────────────────────────────────────────


def test_clean_config_passes_cross_check():
    cfg = _config_obj()
    check = cross_check(cfg, _mdl(), _values(cfg))
    assert check.errors == []
    assert check.warnings == []


def test_an_optional_row_property_is_an_error():
    mdl = _mdl()
    mdl["models"][0]["rowLevelAccessControls"][0]["requiredProperties"][0][
        "required"
    ] = False
    cfg = _config_obj()
    check = cross_check(cfg, mdl, _values(cfg))
    assert any("optional" in e and "drop the rule" in e for e in check.errors)


def test_an_optional_column_property_is_an_error():
    mdl = _mdl()
    mdl["models"][0]["columns"][2]["columnLevelAccessControl"]["requiredProperties"][0][
        "required"
    ] = False
    cfg = _config_obj()
    check = cross_check(cfg, mdl, _values(cfg))
    assert any("column rule" in e and "optional" in e for e in check.errors)


def test_a_non_numeric_value_for_a_numeric_rule_is_an_error():
    cfg = _config_obj()
    values = _values(cfg)
    values["analyst"]["session_level"] = "high"
    check = cross_check(cfg, _mdl(), values)
    assert any("must be numeric" in e for e in check.errors)


def test_a_missing_role_value_is_a_warning():
    cfg = _config_obj()
    values = _values(cfg)
    del values["analyst"]["session_level"]
    check = cross_check(cfg, _mdl(), values)
    assert check.errors == []
    assert any("analyst" in w and "session_level" in w for w in check.warnings)


def test_an_unused_override_is_a_warning():
    cfg = _config_obj()
    values = _values(cfg)
    cfg.roles["manager"].allow_override = ["region"]
    check = cross_check(cfg, _mdl(), values)
    assert any("not used by any rule" in w for w in check.warnings)


def test_report_shows_denied_columns_per_role():
    cfg = _config_obj()
    check = cross_check(cfg, _mdl(), _values(cfg))
    text = format_report(check)
    assert "role analyst" in text
    assert "denied: amount (session_level=1 fails GREATER_THAN_OR_EQUALS 2)" in text
    analyst = next(r for r in check.report if r["role"] == "analyst")
    manager = next(r for r in check.report if r["role"] == "manager")
    assert "amount" not in analyst["columns_allowed"]
    assert "amount" in manager["columns_allowed"]


# ── resolution ──────────────────────────────────────────────────────────────


def _resolve(cfg, values, token_value, **kw):
    return resolve(
        cfg, values, kw.pop("fixed", None), token=find_token(cfg, token_value), **kw
    )


def test_the_default_role_applies_without_a_request_role():
    cfg = _config_obj()
    values = _values(cfg)
    r = _resolve(cfg, values, "shop-secret")
    assert r.role == "analyst"
    assert r.values == {"session_level": 1, "session_customer": "c_001"}
    assert r.sources == {"session_level": "role", "session_customer": "role"}


def test_a_request_can_override_an_allowed_property():
    cfg = _config_obj()
    values = _values(cfg)
    r = _resolve(
        cfg, values, "shop-secret", request_props={"session_customer": "c_002"}
    )
    assert r.values["session_customer"] == "c_002"
    assert r.sources["session_customer"] == "request"
    assert r.sources["session_level"] == "role"


def test_an_override_outside_the_allow_list_is_refused():
    cfg = _config_obj()
    with pytest.raises(AccessError) as exc:
        _resolve(cfg, _values(cfg), "shop-secret", request_props={"session_level": 3})
    assert exc.value.code == "override_not_allowed"


def test_a_token_without_override_permission_is_refused():
    cfg = _config_obj()
    with pytest.raises(AccessError) as exc:
        _resolve(
            cfg, _values(cfg), "bi-secret", request_props={"session_customer": "x"}
        )
    assert exc.value.code == "override_forbidden"


def test_a_token_without_role_permission_cannot_choose_a_role():
    cfg = _config_obj()
    with pytest.raises(AccessError) as exc:
        _resolve(cfg, _values(cfg), "shop-secret", request_role="manager")
    assert exc.value.code == "role_not_allowed"


def test_a_token_allowed_to_choose_a_role_gets_that_role():
    cfg = _config_obj()
    r = _resolve(cfg, _values(cfg), "bi-secret", request_role="analyst")
    assert r.role == "analyst"


def test_an_unknown_role_is_refused():
    cfg = _config_obj()
    with pytest.raises(AccessError) as exc:
        _resolve(cfg, _values(cfg), "bi-secret", request_role="ghost")
    assert exc.value.code == "unknown_role"


def test_a_missing_or_wrong_token_is_unauthorized():
    cfg = _config_obj()
    with pytest.raises(AccessError) as exc:
        _resolve(cfg, _values(cfg), None)
    assert exc.value.status == 401
    with pytest.raises(AccessError):
        _resolve(cfg, _values(cfg), "wrong")


def test_stdio_uses_the_fixed_role_and_refuses_overrides():
    cfg = _config_obj()
    r = resolve(cfg, _values(cfg), None, token=None, stdio_role="manager")
    assert r.role == "manager" and r.token_id is None
    with pytest.raises(AccessError) as exc:
        resolve(
            cfg,
            _values(cfg),
            None,
            token=None,
            stdio_role="manager",
            request_props={"session_customer": "c_002"},
        )
    assert exc.value.code == "override_forbidden"


def test_a_server_fixed_value_wins_and_cannot_be_overridden():
    cfg = _config_obj()
    values = _values(cfg)
    r = _resolve(cfg, values, "shop-secret", fixed={"session_level": 2})
    assert r.values["session_level"] == 2
    assert r.sources["session_level"] == "fixed"
    with pytest.raises(AccessError) as exc:
        _resolve(
            cfg,
            values,
            "shop-secret",
            fixed={"session_level": 2},
            request_props={"session_level": 3},
        )
    assert exc.value.code in {"fixed_property", "override_not_allowed"}


def test_literals_quote_strings_and_keep_numbers():
    assert sql_literal("APAC") == "'APAC'"
    assert sql_literal("O'Brien") == "'O''Brien'"
    assert sql_literal(3) == "3"
    cfg = _config_obj()
    r = _resolve(cfg, _values(cfg), "shop-secret")
    assert r.literals == {"session_level": "1", "session_customer": "'c_001'"}


def test_provenance_lists_each_value_and_source():
    cfg = _config_obj()
    r = _resolve(
        cfg, _values(cfg), "shop-secret", request_props={"session_customer": "c_002"}
    )
    prov = r.provenance()
    assert prov["role"] == "analyst"
    assert prov["properties"]["session_customer"] == {
        "value": "c_002",
        "source": "request",
    }


def test_audit_writes_one_json_line_per_call(tmp_path):
    cfg = _config_obj()
    r = _resolve(cfg, _values(cfg), "shop-secret")
    path = tmp_path / "audit.jsonl"
    write_audit(Audit(path=path, record_sql=True), r, sql="SELECT 1", status="ok")
    write_audit(Audit(path=path, record_sql=False), r, sql="SELECT 2", status="ok")
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    assert lines[0]["sql"] == "SELECT 1" and lines[0]["token"] == "svc_shop"
    assert "sql" not in lines[1]
