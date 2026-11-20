"""Role-based row and column access: the server's access config and request resolution.

Three layers, each with one job:

* the model rules (MDL ``row_level_access_controls`` / ``column_level_access_control``)
  say which session properties control which rows and columns;
* the server's access config (``janus_access.yml``) gives each role its property
  values, computed by a single-row SELECT at startup;
* a request may override some properties, if its token allows it.

Startup cross-checks the three and refuses to run on an error. Per request,
``resolve`` decides the role and the final property values and says where each
value came from. Access-rule properties must be ``required: true``: an optional
one would make the engine drop the rule silently, so that is an error here.
"""

from __future__ import annotations

import hmac
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

ACCESS_VERSION = 1
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_TOP_KEYS = {"version", "roles", "tokens", "audit"}
_ROLE_KEYS = {"sql", "allow_override"}
_TOKEN_KEYS = {"id", "token_env", "default_role", "may_request_role", "may_override"}
_AUDIT_KEYS = {"path", "record_sql"}
_NUMERIC_OPS = {
    "GREATER_THAN",
    "LESS_THAN",
    "GREATER_THAN_OR_EQUALS",
    "LESS_THAN_OR_EQUALS",
}
_OPS = {"EQUALS", "NOT_EQUALS", *_NUMERIC_OPS}


class AccessConfigError(ValueError):
    """The access config or its cross-check with the model is invalid. Startup stops."""


class AccessError(Exception):
    """A request was refused. ``code`` is the stable error code, ``status`` the HTTP status."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class Role:
    name: str
    sql: str
    allow_override: list[str] = field(default_factory=list)


@dataclass
class Token:
    id: str
    value: str
    default_role: str
    may_request_role: bool = False
    may_override: bool = False


@dataclass
class Audit:
    path: Path | None = None
    record_sql: bool = True


@dataclass
class AccessConfig:
    roles: dict[str, Role]
    tokens: list[Token]
    audit: Audit


# ── loading ─────────────────────────────────────────────────────────────────


def _mapping(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        raise AccessConfigError(f"{where} must be a mapping")
    return value


def _unknown(keys: set[str], allowed: set[str], where: str) -> None:
    extra = sorted(keys - allowed)
    if extra:
        raise AccessConfigError(f"{where}: unknown field(s) {', '.join(extra)}")


def _check_single_select(sql: Any, role: str) -> str:
    if not isinstance(sql, str) or not sql.strip():
        raise AccessConfigError(f"role {role!r}: sql must be a non-empty string")
    text = sql.strip()
    if "\n" in text or not text.lower().startswith("select"):
        raise AccessConfigError(f"role {role!r}: sql must be a single-line SELECT")
    if text.rstrip(";").count(";") > 0:
        raise AccessConfigError(f"role {role!r}: sql must be one statement")
    return text.rstrip(";")


def parse_access_config(
    data: Any, env: Mapping[str, str] | None = None
) -> AccessConfig:
    """Validate the parsed YAML. Token values are read from ``token_env``."""
    env = os.environ if env is None else env
    data = _mapping(data, "access config")
    _unknown(set(data), _TOP_KEYS, "access config")
    if data.get("version") != ACCESS_VERSION:
        raise AccessConfigError(f"version must be {ACCESS_VERSION}")

    raw_roles = _mapping(data.get("roles"), "roles")
    if not raw_roles:
        raise AccessConfigError("roles must not be empty")
    roles: dict[str, Role] = {}
    for name, body in raw_roles.items():
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise AccessConfigError(f"role name {name!r} is not a valid identifier")
        body = _mapping(body, f"role {name!r}")
        _unknown(set(body), _ROLE_KEYS, f"role {name!r}")
        overrides = body.get("allow_override") or []
        if not isinstance(overrides, list) or not all(
            isinstance(o, str) for o in overrides
        ):
            raise AccessConfigError(
                f"role {name!r}: allow_override must be a list of names"
            )
        roles[name] = Role(
            name, _check_single_select(body.get("sql"), name), list(overrides)
        )

    raw_tokens = data.get("tokens")
    if not isinstance(raw_tokens, list) or not raw_tokens:
        raise AccessConfigError("tokens must be a non-empty list")
    tokens: list[Token] = []
    seen: set[str] = set()
    for item in raw_tokens:
        item = _mapping(item, "token entry")
        _unknown(set(item), _TOKEN_KEYS, "token entry")
        tid = item.get("id")
        if not isinstance(tid, str) or not tid:
            raise AccessConfigError("token id must be a non-empty string")
        if tid in seen:
            raise AccessConfigError(f"duplicate token id {tid!r}")
        seen.add(tid)
        env_name = item.get("token_env")
        if not isinstance(env_name, str) or not env_name:
            raise AccessConfigError(f"token {tid!r}: token_env is required")
        value = env.get(env_name, "")
        if not value:
            raise AccessConfigError(
                f"token {tid!r}: environment variable {env_name} is empty or unset"
            )
        default = item.get("default_role")
        if default not in roles:
            raise AccessConfigError(
                f"token {tid!r}: default_role {default!r} is not a role"
            )
        tokens.append(
            Token(
                id=tid,
                value=value,
                default_role=default,
                may_request_role=bool(item.get("may_request_role", False)),
                may_override=bool(item.get("may_override", False)),
            )
        )

    audit_raw = _mapping(data.get("audit") or {}, "audit")
    _unknown(set(audit_raw), _AUDIT_KEYS, "audit")
    audit_path = audit_raw.get("path")
    audit = Audit(
        path=Path(audit_path) if audit_path else None,
        record_sql=bool(audit_raw.get("record_sql", True)),
    )
    return AccessConfig(roles=roles, tokens=tokens, audit=audit)


def load_access_config(
    path: Path, env: Mapping[str, str] | None = None
) -> AccessConfig:
    """Read a YAML (or JSON) access config file."""
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AccessConfigError(f"cannot read {path}: {exc}") from exc
    return parse_access_config(data, env)


# ── role values ─────────────────────────────────────────────────────────────

RunSql = Callable[[str], list[dict]]


def evaluate_roles(config: AccessConfig, run_sql: RunSql) -> dict[str, dict[str, Any]]:
    """Run each role's SQL once. Each must return exactly one row with no NULL values.

    A NULL is refused rather than replaced: a substituted value could grant access.
    """
    values: dict[str, dict[str, Any]] = {}
    for role in config.roles.values():
        rows = run_sql(role.sql)
        if len(rows) != 1:
            raise AccessConfigError(
                f"role {role.name!r}: sql must return one row, got {len(rows)}"
            )
        row = rows[0]
        for col in row:
            if not _NAME.fullmatch(str(col)):
                raise AccessConfigError(
                    f"role {role.name!r}: column {col!r} is not a valid name"
                )
        nulls = [str(col) for col, value in row.items() if value is None]
        if nulls:
            raise AccessConfigError(
                f"role {role.name!r}: {', '.join(nulls)} is NULL; give every property a value"
            )
        missing = [o for o in role.allow_override if o not in row]
        if missing:
            raise AccessConfigError(
                f"role {role.name!r}: allow_override {', '.join(missing)} is not a result column"
            )
        values[role.name] = dict(row)
    return values


# ── model rules ─────────────────────────────────────────────────────────────


@dataclass
class RowRule:
    model: str
    name: str
    props: list[tuple[str, bool]]  # (name, required)
    condition: str


@dataclass
class ColumnRule:
    model: str
    column: str
    name: str
    prop: str
    required: bool
    operator: str
    threshold: str


def collect_rules(mdl: dict) -> tuple[list[RowRule], list[ColumnRule]]:
    """Read the access rules from the camelCase MDL manifest (``target/mdl.json``)."""
    rows: list[RowRule] = []
    cols: list[ColumnRule] = []
    for model in mdl.get("models") or []:
        mname = str(model.get("name", ""))
        for rule in model.get("rowLevelAccessControls") or []:
            props = [
                (str(p.get("name")), bool(p.get("required", True)))
                for p in rule.get("requiredProperties") or []
            ]
            rows.append(
                RowRule(
                    mname,
                    str(rule.get("name", "")),
                    props,
                    str(rule.get("condition", "")),
                )
            )
        for column in model.get("columns") or []:
            rule = column.get("columnLevelAccessControl")
            if not rule:
                continue
            props = rule.get("requiredProperties") or []
            prop = props[0] if props else {}
            cols.append(
                ColumnRule(
                    model=mname,
                    column=str(column.get("name", "")),
                    name=str(rule.get("name", "")),
                    prop=str(prop.get("name", "")),
                    required=bool(prop.get("required", True)),
                    operator=str(rule.get("operator", "")),
                    threshold=str(rule.get("threshold", "")),
                )
            )
    return rows, cols


def _compare(value: Any, operator: str, threshold: str) -> bool:
    if operator in _NUMERIC_OPS:
        left, right = float(value), float(threshold)
        return {
            "GREATER_THAN": left > right,
            "LESS_THAN": left < right,
            "GREATER_THAN_OR_EQUALS": left >= right,
            "LESS_THAN_OR_EQUALS": left <= right,
        }[operator]
    same = str(value) == threshold
    return same if operator == "EQUALS" else not same


def _is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


# ── startup cross-check ─────────────────────────────────────────────────────


@dataclass
class Check:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    report: list[dict] = field(default_factory=list)


def cross_check(
    config: AccessConfig,
    mdl: dict,
    role_values: dict[str, dict[str, Any]],
    fixed: Mapping[str, Any] | None = None,
) -> Check:
    """Compare roles, overrides, and model rules. Errors stop startup; warnings do not."""
    fixed = dict(fixed or {})
    rows, cols = collect_rules(mdl)
    check = Check()

    for rule in rows:
        for pname, required in rule.props:
            if not required:
                check.errors.append(
                    f"row rule {rule.model}.{rule.name}: property {pname} is optional; "
                    "an absent property would drop the rule silently, so it must be required"
                )
    for rule in cols:
        if not rule.required:
            check.errors.append(
                f"column rule {rule.model}.{rule.column} ({rule.name}): property {rule.prop} "
                "is optional; it must be required"
            )
        if rule.operator not in _OPS:
            check.errors.append(
                f"column rule {rule.name}: unknown operator {rule.operator}"
            )

    used = {p for r in rows for p, _ in r.props} | {r.prop for r in cols}
    for rule in cols:
        if rule.operator in _NUMERIC_OPS and not _is_number(rule.threshold):
            check.errors.append(
                f"column rule {rule.name}: threshold {rule.threshold!r} is not a number"
            )
        for role, values in role_values.items():
            if rule.prop in values and rule.operator in _NUMERIC_OPS:
                if not isinstance(values[rule.prop], (int, float)) or isinstance(
                    values[rule.prop], bool
                ):
                    check.errors.append(
                        f"role {role!r}: {rule.prop} must be numeric to compare with {rule.threshold} "
                        f"in rule {rule.name}"
                    )

    for name, role in config.roles.items():
        values = role_values[name]
        for override in role.allow_override:
            if override not in used:
                check.warnings.append(
                    f"role {name!r}: override {override} is not used by any rule"
                )
        for prop in values:
            if prop not in used:
                check.warnings.append(
                    f"role {name!r}: property {prop} is not used by any rule"
                )
            if prop in fixed:
                check.warnings.append(
                    f"property {prop} is fixed by --property and overrides role {name!r}"
                )

    for rule in rows + cols:
        needed = (
            [p for p, _ in rule.props] if isinstance(rule, RowRule) else [rule.prop]
        )
        for name in config.roles:
            missing = [
                p for p in needed if p not in role_values[name] and p not in fixed
            ]
            if missing:
                check.warnings.append(
                    f"role {name!r} has no value for {', '.join(missing)} used by {rule.model}; "
                    "queries on that model will fail for it"
                )

    check.report = _report(config, rows, cols, role_values, fixed)
    return check


def _report(config, rows, cols, role_values, fixed) -> list[dict]:
    out: list[dict] = []
    models = sorted({r.model for r in rows} | {c.model for c in cols})
    for role in config.roles:
        values = {**role_values[role], **fixed}
        for model in models:
            conditions = [f"{r.name}: {r.condition}" for r in rows if r.model == model]
            denied, allowed = [], []
            for c in cols:
                if c.model != model:
                    continue
                if c.prop not in values:
                    denied.append(f"{c.column} (no {c.prop})")
                else:
                    try:
                        ok = _compare(values[c.prop], c.operator, c.threshold)
                    except (TypeError, ValueError):
                        denied.append(
                            f"{c.column} ({c.prop}={values[c.prop]} is not comparable)"
                        )
                        continue
                    if ok:
                        allowed.append(c.column)
                    else:
                        denied.append(
                            f"{c.column} ({c.prop}={values[c.prop]} fails {c.operator} {c.threshold})"
                        )
            out.append(
                {
                    "role": role,
                    "model": model,
                    "row_rules": conditions,
                    "columns_allowed": allowed,
                    "columns_denied": denied,
                }
            )
    return out


def format_report(check: Check) -> str:
    lines = []
    for row in check.report:
        lines.append(f"role {row['role']}  model {row['model']}")
        for cond in row["row_rules"]:
            lines.append(f"    rows: {cond}")
        if row["columns_allowed"]:
            lines.append(f"    columns: {', '.join(row['columns_allowed'])}")
        for denied in row["columns_denied"]:
            lines.append(f"    denied: {denied}")
    for warning in check.warnings:
        lines.append(f"warning: {warning}")
    for error in check.errors:
        lines.append(f"error: {error}")
    return "\n".join(lines)


# ── per request ─────────────────────────────────────────────────────────────


def sql_literal(value: Any) -> str:
    """A property value as the SQL literal the engine expects (strings quoted)."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AccessError("invalid_property", "property values must be finite", 400)
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise AccessError(
        "invalid_property", f"unsupported value type {type(value).__name__}", 400
    )


@dataclass
class Resolved:
    role: str | None
    token_id: str | None
    values: dict[str, Any]
    sources: dict[str, str]

    @property
    def literals(self) -> dict[str, str] | None:
        return {k: sql_literal(v) for k, v in self.values.items()} or None

    def provenance(self) -> dict:
        return {
            "role": self.role,
            "properties": {
                k: {"value": self.values[k], "source": self.sources[k]}
                for k in self.values
            },
        }


def find_token(config: AccessConfig, presented: str | None) -> Token | None:
    """The token entry whose value matches the presented bearer token, compared in constant time."""
    if not presented:
        return None
    found = None
    for entry in config.tokens:
        if hmac.compare_digest(presented.encode(), entry.value.encode()):
            found = entry
    return found


def resolve(
    config: AccessConfig,
    role_values: dict[str, dict[str, Any]],
    fixed: Mapping[str, Any] | None,
    *,
    token: Token | None,
    stdio_role: str | None = None,
    request_role: str | None = None,
    request_props: Mapping[str, Any] | None = None,
) -> Resolved:
    """Decide the role and the property values for one request. Raises AccessError."""
    fixed = dict(fixed or {})
    if token is None:
        if stdio_role is None:
            raise AccessError("unauthorized", "missing or invalid bearer token", 401)
        role_name = stdio_role
        may_request, may_override = False, False
        token_id = None
    else:
        role_name = token.default_role
        may_request, may_override = token.may_request_role, token.may_override
        token_id = token.id

    if request_role is not None:
        if not may_request:
            raise AccessError(
                "role_not_allowed", "this token may not choose a role", 403
            )
        role_name = request_role
    if role_name not in config.roles:
        raise AccessError("unknown_role", f"role {role_name!r} is not configured", 403)
    role = config.roles[role_name]

    values = dict(role_values[role_name])
    sources = {k: "role" for k in values}
    for name, value in (request_props or {}).items():
        if not may_override:
            raise AccessError(
                "override_forbidden", "this token may not override properties", 403
            )
        if name in fixed:
            raise AccessError(
                "fixed_property", f"property {name} is set by the server", 403
            )
        if name not in role.allow_override:
            raise AccessError(
                "override_not_allowed", f"property {name} may not be overridden", 403
            )
        values[name] = value
        sources[name] = "request"
    for name, value in fixed.items():
        values[name] = value
        sources[name] = "fixed"
    return Resolved(role_name, token_id, values, sources)


def write_audit(
    audit: Audit,
    resolved: Resolved,
    *,
    sql: str,
    status: str,
    error: str | None = None,
) -> None:
    """Append one JSON line for the request. Skipped when no audit path is configured."""
    if audit.path is None:
        return
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "token": resolved.token_id,
        "role": resolved.role,
        "properties": resolved.provenance()["properties"],
        "status": status,
    }
    if audit.record_sql:
        entry["sql"] = sql
    if error:
        entry["error"] = error
    audit.path.parent.mkdir(parents=True, exist_ok=True)
    with audit.path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


# ── runtime ─────────────────────────────────────────────────────────────────


@dataclass
class Runtime:
    config: AccessConfig
    role_values: dict[str, dict[str, Any]]
    fixed: dict[str, Any]
    check: Check


def build_runtime(
    config: AccessConfig,
    mdl: dict,
    run_sql: RunSql,
    fixed: Mapping[str, Any] | None = None,
) -> Runtime:
    """Evaluate the roles, cross-check them with the model, and refuse on any error."""
    fixed = dict(fixed or {})
    role_values = evaluate_roles(config, run_sql)
    check = cross_check(config, mdl, role_values, fixed)
    if check.errors:
        raise AccessConfigError("; ".join(check.errors))
    return Runtime(config=config, role_values=role_values, fixed=fixed, check=check)


def prepare_call(
    *,
    runtime: Runtime | None,
    fixed: Mapping[str, Any] | None,
    trusted: bool,
    presented: str | None,
    stdio_role: str | None = None,
    request_role: str | None = None,
    request_props: Mapping[str, Any] | None = None,
) -> Resolved:
    """The one entry point MCP and HTTP use to turn a request into property values.

    With an access config, the caller's token (or the stdio role) decides everything.
    Without one, a request may pass properties only when ``trusted`` (a token holder,
    or the operator's --trust-client-properties), and server-fixed values still win.
    """
    if runtime is not None:
        return resolve(
            runtime.config,
            runtime.role_values,
            runtime.fixed,
            token=find_token(runtime.config, presented),
            stdio_role=stdio_role,
            request_role=request_role,
            request_props=request_props,
        )
    fixed = dict(fixed or {})
    if request_role is not None:
        raise AccessError(
            "role_not_allowed", "roles need an access config (--access-config)", 403
        )
    props = dict(request_props or {})
    if props and not trusted:
        raise AccessError("override_forbidden", "properties need a trusted caller", 403)
    for name in props:
        if name in fixed:
            raise AccessError(
                "fixed_property", f"property {name} is set by the server", 403
            )
    values = {**props, **fixed}
    sources = {k: ("fixed" if k in fixed else "request") for k in values}
    return Resolved(None, None, values, sources)


def table_rows(table: Any) -> list[dict]:
    """An Arrow table as a list of dicts, for role SQL results."""
    return table.to_pylist()


def write_refusal(
    audit: Audit,
    token_id: str | None,
    *,
    sql: str,
    error: AccessError,
) -> None:
    """Audit a request refused before it ran (bad token, role, or override)."""
    if audit.path is None:
        return
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "token": token_id,
        "status": "denied",
        "code": error.code,
        "error": str(error),
    }
    if audit.record_sql:
        entry["sql"] = sql
    audit.path.parent.mkdir(parents=True, exist_ok=True)
    with audit.path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
