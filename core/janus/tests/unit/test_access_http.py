"""HTTP API with role-based access: tokens, roles, overrides, and the rows each role gets."""

from __future__ import annotations

import base64
import json

import duckdb
import pytest
import yaml
from starlette.testclient import TestClient

from janus.access import build_runtime, load_access_config, table_rows
from janus.api_server import build_app
from janus.engine import JanusEngine
from janus.mcp_server import ServeContext
from janus.model.data_source import DataSource
from tests.unit.conftest import manifest_b64, model_dict

pytestmark = pytest.mark.unit

ANALYST = {"Authorization": "Bearer analyst-secret"}
MANAGER = {"Authorization": "Bearer manager-secret"}


@pytest.fixture
def warehouse(tmp_path):
    directory = tmp_path / "warehouse"
    directory.mkdir()
    conn = duckdb.connect(str(directory / "shop.duckdb"))
    conn.execute("CREATE TABLE customers (customer_id INTEGER, region VARCHAR)")
    conn.execute("INSERT INTO customers VALUES (1, 'APAC'), (2, 'EU')")
    conn.execute(
        "CREATE TABLE orders (order_id INTEGER, customer_id INTEGER, amount DECIMAL(10,2))"
    )
    conn.execute("INSERT INTO orders VALUES (10, 1, 9.5), (11, 2, 20.0)")
    conn.close()
    return directory


@pytest.fixture
def project(make_project):
    customers = model_dict(
        "customers",
        "customers",
        [("customer_id", "INTEGER"), ("region", "VARCHAR")],
        primary_key="customer_id",
    )
    orders = model_dict(
        "orders",
        "orders",
        [("order_id", "INTEGER"), ("customer_id", "INTEGER"), ("amount", "DECIMAL")],
        primary_key="order_id",
    )
    orders["columns"][2]["columnLevelAccessControl"] = {
        "name": "amount_for_managers",
        "requiredProperties": [{"name": "session_level", "required": True}],
        "operator": "GREATER_THAN_OR_EQUALS",
        "threshold": "2",
    }
    orders["rowLevelAccessControls"] = [
        {
            "name": "own_or_manager",
            "requiredProperties": [
                {"name": "session_customer", "required": True},
                {"name": "session_level", "required": True},
            ],
            "condition": "customer_id = @session_customer OR @session_level >= 3",
        }
    ]
    return make_project([customers, orders])


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TOK_ANALYST", "analyst-secret")
    monkeypatch.setenv("TOK_MANAGER", "manager-secret")
    audit = tmp_path / "audit.jsonl"
    body = {
        "version": 1,
        "roles": {
            "analyst": {
                "sql": "SELECT 1 AS session_level, 1 AS session_customer",
                "allow_override": ["session_customer"],
            },
            "manager": {
                "sql": "SELECT 3 AS session_level, 0 AS session_customer",
                "allow_override": [],
            },
        },
        "tokens": [
            {
                "id": "svc_analyst",
                "token_env": "TOK_ANALYST",
                "default_role": "analyst",
                "may_request_role": False,
                "may_override": True,
            },
            {
                "id": "svc_manager",
                "token_env": "TOK_MANAGER",
                "default_role": "manager",
                "may_request_role": True,
                "may_override": False,
            },
        ],
        "audit": {"path": str(audit), "record_sql": True},
    }
    path = tmp_path / "janus_access.yml"
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path, audit


@pytest.fixture
def client(project, warehouse, config_file):
    path, _ = config_file
    mdl = json.loads(base64.b64decode(manifest_b64(project)))
    engine = JanusEngine(
        manifest_b64(project),
        DataSource.duckdb,
        {"url": str(warehouse), "format": "duckdb"},
        fallback=False,
    )
    try:
        runtime = build_runtime(
            load_access_config(path),
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
        yield TestClient(build_app(ctx, token=None))
    finally:
        engine.close()


def _query(client, headers, sql, **extra):
    return client.post("/query", json={"sql": sql, **extra}, headers=headers)


def _ids(response):
    return sorted(row["order_id"] for row in response.json()["rows"])


def test_no_token_is_unauthorized(client):
    r = client.post("/dry-plan", json={"sql": "SELECT order_id FROM orders"})
    assert r.status_code == 401


def test_an_unknown_token_is_unauthorized(client):
    r = client.post(
        "/dry-plan",
        json={"sql": "SELECT order_id FROM orders"},
        headers={"Authorization": "Bearer nope"},
    )
    assert r.status_code == 401


def test_the_analyst_sees_only_their_own_rows(client):
    r = _query(client, ANALYST, "SELECT order_id FROM orders")
    assert r.status_code == 200, r.text
    assert _ids(r) == [10]


def test_the_manager_sees_every_row(client):
    r = _query(client, MANAGER, "SELECT order_id FROM orders")
    assert r.status_code == 200, r.text
    assert _ids(r) == [10, 11]


def test_the_analyst_cannot_read_the_restricted_column(client):
    r = _query(client, ANALYST, "SELECT order_id, amount FROM orders")
    assert r.status_code == 422
    assert "Permission Denied" in r.json()["error"]


def test_the_manager_can_read_the_restricted_column(client):
    r = _query(client, MANAGER, "SELECT order_id, amount FROM orders")
    assert r.status_code == 200, r.text


def test_an_allowed_override_changes_the_rows(client):
    r = _query(
        client,
        ANALYST,
        "SELECT order_id FROM orders",
        properties={"session_customer": 2},
    )
    assert r.status_code == 200, r.text
    assert _ids(r) == [11]
    prov = r.json()["provenance"]
    assert prov["role"] == "analyst"
    assert prov["properties"]["session_customer"] == {"value": 2, "source": "request"}
    assert prov["properties"]["session_level"]["source"] == "role"


def test_an_override_is_refused_for_a_token_without_permission(client):
    r = _query(
        client,
        MANAGER,
        "SELECT order_id FROM orders",
        properties={"session_customer": 1},
    )
    assert r.status_code == 403
    assert r.json()["code"] == "override_forbidden"


def test_an_override_outside_the_allow_list_is_refused(client):
    r = _query(
        client, ANALYST, "SELECT order_id FROM orders", properties={"session_level": 3}
    )
    assert r.status_code == 403
    assert r.json()["code"] == "override_not_allowed"


def test_the_analyst_cannot_choose_a_role(client):
    r = _query(client, ANALYST, "SELECT order_id FROM orders", role="manager")
    assert r.status_code == 403
    assert r.json()["code"] == "role_not_allowed"


def test_the_manager_may_act_as_the_analyst(client):
    r = _query(client, MANAGER, "SELECT order_id, amount FROM orders", role="analyst")
    assert r.status_code == 422
    assert "Permission Denied" in r.json()["error"]


def test_an_unknown_role_is_refused(client):
    r = _query(client, MANAGER, "SELECT order_id FROM orders", role="ghost")
    assert r.status_code == 403
    assert r.json()["code"] == "unknown_role"


def test_dry_plan_shows_the_role_filter(client):
    r = client.post(
        "/dry-plan", json={"sql": "SELECT order_id FROM orders"}, headers=ANALYST
    )
    assert r.status_code == 200, r.text
    assert "customer_id = 1" in r.json()["sql"]


def test_every_call_is_audited(client, config_file):
    _, audit = config_file
    _query(client, ANALYST, "SELECT order_id FROM orders")
    _query(client, ANALYST, "SELECT order_id, amount FROM orders")
    _query(client, ANALYST, "SELECT order_id FROM orders", role="manager")
    lines = [json.loads(x) for x in audit.read_text().splitlines()]
    assert [line["status"] for line in lines] == ["ok", "error", "denied"]
    assert lines[2]["code"] == "role_not_allowed"
    assert lines[2]["token"] == "svc_analyst"
    assert lines[0]["token"] == "svc_analyst"
    assert lines[0]["role"] == "analyst"
    assert lines[0]["sql"] == "SELECT order_id FROM orders"
