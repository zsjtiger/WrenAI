"""HTTP API (``janus serve api``) over the same engine and project as the MCP server.

Query handling is shared with the MCP tools: ``POST /query`` runs through
``mcp_server._query_with_limit_probe``, so row limits, provenance and
certification warnings match ``run_sql`` exactly.

Endpoints (JSON in and out):

* ``GET  /health``            liveness
* ``GET  /models``            models with certification
* ``GET  /models/{name}``     one model's columns, key and certification
* ``POST /query``             ``{"sql", "limit"?, "knowledge"?, "include_sql"?}``
* ``POST /dry-plan``          ``{"sql"}`` expanded target-dialect SQL, no database

Authentication: a bearer token is required whenever the server is not bound to
a loopback address. Compare with ``hmac.compare_digest``; the token is never
logged.
"""

from __future__ import annotations

import hmac
import ipaddress
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from janus.access import (
    AccessError,
    find_token,
    prepare_call,
    write_audit,
    write_refusal,
)
from janus.mcp_server import ServeContext, _query_with_limit_probe
from janus.model.error import JanusError


def is_loopback(host: str) -> bool:
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _audit_http(
    ctx: ServeContext, resolved, sql: str, status: str, error: str | None = None
) -> None:
    if ctx.access is not None:
        write_audit(
            ctx.access.config.audit, resolved, sql=sql, status=status, error=error
        )


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _models_payload(ctx: ServeContext) -> dict[str, Any]:
    from janus.context import load_models  # noqa: PLC0415
    from janus.model.certification import is_certified  # noqa: PLC0415

    return {
        "models": [
            {
                "name": m.get("name"),
                "column_count": len(m.get("columns") or []),
                "certified": is_certified(m.get("properties")),
            }
            for m in load_models(ctx.project)
        ]
    }


def _model_payload(ctx: ServeContext, name: str) -> dict[str, Any] | None:
    from janus.context import load_models  # noqa: PLC0415
    from janus.model.certification import is_certified  # noqa: PLC0415

    model = next((m for m in load_models(ctx.project) if m.get("name") == name), None)
    if model is None:
        return None
    return {
        "name": model.get("name"),
        "columns": [
            {"name": c.get("name"), "type": c.get("type")}
            for c in model.get("columns") or []
        ],
        "primary_key": model.get("primary_key"),
        "certified": is_certified(model.get("properties")),
        "properties": model.get("properties") or {},
    }


def _presented(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None


def _refuse_http(
    ctx: ServeContext, request: Request, sql: str, exc: AccessError
) -> None:
    if ctx.access is not None:
        token = find_token(ctx.access.config, _presented(request))
        write_refusal(
            ctx.access.config.audit, token.id if token else None, sql=sql, error=exc
        )


def _access_error(exc: AccessError) -> JSONResponse:
    return JSONResponse({"error": str(exc), "code": exc.code}, status_code=exc.status)


def _prepare_request(ctx: ServeContext, request: Request, body: dict[str, Any]):
    """Resolve the role and property values for one request. Raises AccessError."""
    role = body.get("role")
    if role is not None and not isinstance(role, str):
        raise AccessError("bad_request", "'role' must be text", 400)
    props = body.get("properties")
    if props is not None and not isinstance(props, dict):
        raise AccessError("bad_request", "'properties' must be an object", 400)
    presented = _presented(request)
    return prepare_call(
        runtime=ctx.access,
        fixed=ctx.fixed_properties,
        trusted=presented is not None or ctx.trust_client_properties,
        presented=presented,
        request_role=role,
        request_props=props,
    )


def build_app(ctx: ServeContext, *, token: str | None) -> Starlette:
    """Build the Starlette application.

    With an access config, every request needs one of its tokens. Otherwise
    ``token`` (if given) is the single bearer token, and ``None`` disables auth.
    """

    def guarded(handler: Callable[[Request], Awaitable[Response]]):
        async def wrapper(request: Request) -> Response:
            if ctx.access is not None:
                if find_token(ctx.access.config, _presented(request)) is None:
                    return _error(401, "missing or invalid bearer token")
            elif token is not None:
                presented = request.headers.get("authorization", "")
                if not hmac.compare_digest(presented, f"Bearer {token}"):
                    return _error(401, "missing or invalid bearer token")
            return await handler(request)

        return wrapper

    async def health(request: Request) -> Response:
        return JSONResponse({"ok": True})

    async def models(request: Request) -> Response:
        return JSONResponse(await run_in_threadpool(_models_payload, ctx))

    async def model(request: Request) -> Response:
        name = request.path_params["name"]
        payload = await run_in_threadpool(_model_payload, ctx, name)
        if payload is None:
            return _error(404, f"model '{name}' not found")
        return JSONResponse(payload)

    async def query(request: Request) -> Response:
        if ctx.no_connect:
            return _error(503, "query is disabled (server started with --no-connect)")
        body = await _json_body(request)
        sql = body.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return _error(400, "'sql' must be a non-empty string")
        try:
            resolved = _prepare_request(ctx, request, body)
            literals = resolved.literals
        except AccessError as exc:
            _refuse_http(ctx, request, sql, exc)
            return _access_error(exc)
        try:
            result = await run_in_threadpool(
                partial(
                    _query_with_limit_probe,
                    ctx,
                    sql,
                    body.get("limit"),
                    knowledge=body.get("knowledge"),
                    include_sql=bool(body.get("include_sql", False)),
                    properties=literals,
                )
            )
        except ValueError as exc:
            _audit_http(ctx, resolved, sql, "error", str(exc))
            return _error(400, str(exc))
        except JanusError as exc:
            _audit_http(ctx, resolved, sql, "error", str(exc))
            return _error(422, str(exc))
        _audit_http(ctx, resolved, sql, "ok")
        if ctx.access is not None:
            result.setdefault("provenance", {}).update(resolved.provenance())
        return JSONResponse(result)

    async def dry_plan(request: Request) -> Response:
        body = await _json_body(request)
        sql = body.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return _error(400, "'sql' must be a non-empty string")
        try:
            resolved = _prepare_request(ctx, request, body)
            literals = resolved.literals
            planned = await run_in_threadpool(ctx.engine.dry_plan, sql, literals)
        except AccessError as exc:
            _refuse_http(ctx, request, sql, exc)
            return _access_error(exc)
        except JanusError as exc:
            return _error(422, str(exc))
        return JSONResponse({"sql": planned})

    routes = [
        Route("/health", guarded(health), methods=["GET"]),
        Route("/models", guarded(models), methods=["GET"]),
        Route("/models/{name}", guarded(model), methods=["GET"]),
        Route("/query", guarded(query), methods=["POST"]),
        Route("/dry-plan", guarded(dry_plan), methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    app.state.janus = ctx
    return app


async def _json_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def run_api(ctx: ServeContext, *, host: str, port: int, token: str | None) -> None:
    """Serve the API with uvicorn. Refuses a non-loopback bind without a token."""
    import uvicorn  # noqa: PLC0415

    if not is_loopback(host) and not token and ctx.access is None:
        raise ValueError(
            "refusing to bind a non-loopback address without a token; "
            "pass --token, set JANUS_API_TOKEN, or use --access-config"
        )
    app = build_app(ctx, token=token)
    uvicorn.run(app, host=host, port=port, log_level="info")
