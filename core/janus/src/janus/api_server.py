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
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from janus.mcp_server import ServeContext, _query_with_limit_probe
from janus.model.error import JanusError


def is_loopback(host: str) -> bool:
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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


def build_app(ctx: ServeContext, *, token: str | None) -> Starlette:
    """Build the Starlette application. ``token=None`` disables authentication."""

    def guarded(handler: Callable[[Request], Awaitable[Response]]):
        async def wrapper(request: Request) -> Response:
            if token is not None:
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
            result = await run_in_threadpool(
                _query_with_limit_probe,
                ctx,
                sql,
                body.get("limit"),
                knowledge=body.get("knowledge"),
                include_sql=bool(body.get("include_sql", False)),
            )
        except ValueError as exc:
            return _error(400, str(exc))
        except JanusError as exc:
            return _error(422, str(exc))
        return JSONResponse(result)

    async def dry_plan(request: Request) -> Response:
        body = await _json_body(request)
        sql = body.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return _error(400, "'sql' must be a non-empty string")
        try:
            planned = await run_in_threadpool(ctx.engine.dry_plan, sql)
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

    if not is_loopback(host) and not token:
        raise ValueError(
            "refusing to bind a non-loopback address without a token; "
            "pass --token or set JANUS_API_TOKEN"
        )
    app = build_app(ctx, token=token)
    uvicorn.run(app, host=host, port=port, log_level="info")
