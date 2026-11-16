"""MCP over HTTP: bearer token gate and trust for token holders."""

from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from janus.mcp_server import (
    ServeContext,
    bearer_guard,
    build_server,
    merge_properties,
    prepare_http_context,
)

pytestmark = pytest.mark.unit

TOKEN = "mcp-token"


def _inner(scope, receive, send):
    async def app(scope, receive, send):
        response = PlainTextResponse("reached")
        await response(scope, receive, send)

    return app


def _ctx(**kw):
    base = dict(
        project=None,
        engine=None,
        allow_write=False,
        no_connect=True,
        protected_properties=frozenset({"session_customer"}),
    )
    base.update(kw)
    return ServeContext(**base)


def test_guard_rejects_a_request_without_the_token():
    client = TestClient(bearer_guard(_inner(None, None, None), TOKEN))
    r = client.get("/mcp")
    assert r.status_code == 401
    assert "bearer" in r.json()["error"]


def test_guard_rejects_a_wrong_token():
    client = TestClient(bearer_guard(_inner(None, None, None), TOKEN))
    r = client.get("/mcp", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_guard_passes_the_right_token():
    client = TestClient(bearer_guard(_inner(None, None, None), TOKEN))
    r = client.get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.text == "reached"


def test_real_mcp_app_needs_the_token_and_answers_initialize():
    app = bearer_guard(FastMCP("janus-test").streamable_http_app(), TOKEN)
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"},
        },
    }
    headers = {"Accept": "application/json, text/event-stream"}
    with TestClient(app, base_url="http://127.0.0.1:8080") as client:
        denied = client.post("/mcp", json=body, headers=headers)
        assert denied.status_code == 401
        allowed = client.post(
            "/mcp", json=body, headers={**headers, "Authorization": f"Bearer {TOKEN}"}
        )
        assert allowed.status_code == 200, allowed.text


def test_token_holder_context_trusts_access_properties():
    ctx = prepare_http_context(_ctx(), TOKEN)
    assert ctx.trust_client_properties is True


def test_no_token_keeps_the_default_refusal():
    ctx = prepare_http_context(_ctx(), None)
    assert ctx.trust_client_properties is False


def test_no_token_with_the_operator_flag_trusts():
    ctx = prepare_http_context(_ctx(trust_client_properties=True), None)
    assert ctx.trust_client_properties is True


def test_fixed_values_still_cannot_be_overridden_over_http():
    ctx = prepare_http_context(_ctx(fixed_properties={"session_customer": 7}), TOKEN)
    with pytest.raises(ValueError, match="set by the server"):
        merge_properties(ctx, {"session_customer": 8})


def test_tools_built_for_http_accept_the_token_holders_property():
    class Engine:
        def __init__(self):
            self.seen = None

        def dry_plan(self, sql, properties=None):
            self.seen = properties
            return "ok"

    engine = Engine()
    ctx = prepare_http_context(_ctx(engine=engine, no_connect=False), TOKEN)
    tool = build_server(ctx)._tool_manager._tools["dry_plan"].fn
    tool("SELECT 1", {"session_customer": 7})
    assert engine.seen == {"session_customer": "7"}
