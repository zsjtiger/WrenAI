"""MCP over HTTP with role-based access: the token in the request picks the role."""

from __future__ import annotations

import base64
import json

import pytest
from starlette.testclient import TestClient

from janus.access import build_runtime, find_token, load_access_config, table_rows
from janus.engine import JanusEngine
from janus.mcp_server import ServeContext, build_server, token_guard
from janus.model.data_source import DataSource
from tests.unit.conftest import manifest_b64
from tests.unit.test_access_http import (  # noqa: F401 (pytest fixtures)
    ANALYST,
    MANAGER,
    config_file,
    project,
    warehouse,
)

pytestmark = pytest.mark.unit

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
HOST = "http://127.0.0.1:8080"


@pytest.fixture
def mcp_client(project, warehouse, config_file):  # noqa: F811
    path, _ = config_file
    mdl = json.loads(base64.b64decode(manifest_b64(project)))
    engine = JanusEngine(
        manifest_b64(project),
        DataSource.duckdb,
        {"url": str(warehouse), "format": "duckdb"},
        fallback=False,
    )
    try:
        config = load_access_config(path)
        runtime = build_runtime(
            config,
            mdl,
            lambda sql: table_rows(engine.query_with_provenance(sql, 10, None)[0]),
        )
        ctx = ServeContext(
            project=project,
            engine=engine,
            allow_write=False,
            no_connect=False,
            access=runtime,
        )
        app = token_guard(
            build_server(ctx).streamable_http_app(),
            lambda presented: find_token(config, presented) is not None,
        )
        with TestClient(app, base_url=HOST) as client:
            yield client
    finally:
        engine.close()


def _initialize(client, headers):
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }
    r = client.post("/mcp", json=body, headers={**HEADERS, **headers})
    assert r.status_code == 200, r.text
    session = r.headers["mcp-session-id"]
    client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={**HEADERS, **headers, "mcp-session-id": session},
    )
    return session


def _call(client, headers, session, sql, **arguments):
    body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "run_sql", "arguments": {"sql": sql, **arguments}},
    }
    r = client.post(
        "/mcp", json=body, headers={**HEADERS, **headers, "mcp-session-id": session}
    )
    assert r.status_code == 200, r.text
    data = next(line[5:] for line in r.text.splitlines() if line.startswith("data:"))
    return json.loads(data)["result"]


def test_mcp_without_a_token_is_unauthorized(mcp_client):
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
    r = mcp_client.post("/mcp", json=body, headers=HEADERS)
    assert r.status_code == 401


def test_the_analyst_token_gets_the_analyst_rows(mcp_client):
    session = _initialize(mcp_client, ANALYST)
    result = _call(
        mcp_client, ANALYST, session, "SELECT order_id FROM orders ORDER BY order_id"
    )
    payload = json.loads(result["content"][0]["text"])
    assert [row["order_id"] for row in payload["rows"]] == [10]
    assert payload["provenance"]["role"] == "analyst"


def test_the_manager_token_gets_every_row(mcp_client):
    session = _initialize(mcp_client, MANAGER)
    result = _call(
        mcp_client, MANAGER, session, "SELECT order_id FROM orders ORDER BY order_id"
    )
    payload = json.loads(result["content"][0]["text"])
    assert [row["order_id"] for row in payload["rows"]] == [10, 11]


def test_a_refused_override_is_a_tool_error(mcp_client):
    session = _initialize(mcp_client, ANALYST)
    result = _call(
        mcp_client,
        ANALYST,
        session,
        "SELECT order_id FROM orders",
        properties={"session_level": 3},
    )
    assert result.get("isError") is True
    assert "override_not_allowed" in result["content"][0]["text"]


def test_a_restricted_column_is_a_tool_error(mcp_client):
    session = _initialize(mcp_client, ANALYST)
    result = _call(mcp_client, ANALYST, session, "SELECT order_id, amount FROM orders")
    assert result.get("isError") is True
    assert "Permission Denied" in result["content"][0]["text"]
