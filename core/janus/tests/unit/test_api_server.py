"""HTTP API: routes, authentication, and error mapping over a real engine."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from janus.api_server import build_app, is_loopback, run_api
from janus.engine import JanusEngine
from janus.mcp_server import ServeContext
from janus.model.data_source import DataSource
from tests.unit.conftest import manifest_b64, model_dict, shop_connection_info

pytestmark = pytest.mark.unit

TOKEN = "s3cret-token"


@pytest.fixture
def api_project(make_project):
    customers = model_dict(
        "customers",
        "customers",
        [("id", "INTEGER"), ("name", "VARCHAR")],
        primary_key="id",
        properties={"certified": "true"},
    )
    orders = model_dict(
        "orders",
        "orders",
        [("order_id", "INTEGER"), ("cust_id", "INTEGER")],
        primary_key="order_id",
    )
    return make_project([customers, orders])


@pytest.fixture
def client_factory(api_project, shop_dir):
    engines = []

    def _make(token=None, no_connect=False):
        engine = JanusEngine(
            manifest_b64(api_project),
            DataSource.duckdb,
            shop_connection_info(shop_dir),
            fallback=False,
        )
        engines.append(engine)
        ctx = ServeContext(
            project=api_project, engine=engine, allow_write=False, no_connect=no_connect
        )
        return TestClient(build_app(ctx, token=token))

    yield _make
    for engine in engines:
        engine.close()


def test_health_needs_no_engine_work(client_factory):
    response = client_factory().get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_models_include_certification(client_factory):
    body = client_factory().get("/models").json()
    assert {m["name"]: m["certified"] for m in body["models"]} == {
        "customers": True,
        "orders": False,
    }


def test_unknown_model_is_404(client_factory):
    response = client_factory().get("/models/ghost")
    assert response.status_code == 404


def test_query_returns_rows_and_provenance(client_factory):
    response = client_factory().post(
        "/query", json={"sql": 'SELECT name FROM "customers"', "limit": 5}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["provenance"]["models"] == ["customers"]
    assert "warnings" not in body


def test_query_warns_when_a_model_is_uncertified(client_factory):
    body = (
        client_factory()
        .post("/query", json={"sql": 'SELECT order_id FROM "orders"'})
        .json()
    )
    assert body["warnings"] == ["model 'orders' is not certified"]


def test_bad_limit_is_a_client_error(client_factory):
    response = client_factory().post(
        "/query", json={"sql": 'SELECT name FROM "customers"', "limit": -1}
    )
    assert response.status_code == 400


def test_invalid_sql_is_reported_not_crashed(client_factory):
    response = client_factory().post("/query", json={"sql": "SELECT * FROM nope_model"})
    assert response.status_code == 422
    assert "error" in response.json()


def test_dry_plan_returns_expanded_sql(client_factory):
    response = client_factory().post(
        "/dry-plan", json={"sql": 'SELECT name FROM "customers"'}
    )
    assert response.status_code == 200
    assert "customers" in response.json()["sql"].lower()


def test_query_requires_sql(client_factory):
    response = client_factory().post("/query", json={})
    assert response.status_code == 400


def test_no_connect_disables_query(client_factory):
    response = client_factory(no_connect=True).post(
        "/query", json={"sql": 'SELECT name FROM "customers"'}
    )
    assert response.status_code == 503


def test_token_is_required_when_configured(client_factory):
    client = client_factory(token=TOKEN)
    assert client.get("/models").status_code == 401
    assert (
        client.get("/models", headers={"Authorization": "Bearer wrong"}).status_code
        == 401
    )
    ok = client.get("/models", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ok.status_code == 200


def test_non_loopback_bind_requires_a_token(api_project, shop_dir):
    ctx = ServeContext(
        project=api_project, engine=None, allow_write=False, no_connect=True
    )
    with pytest.raises(ValueError, match="non-loopback"):
        run_api(ctx, host="0.0.0.0", port=0, token=None)


@pytest.mark.parametrize(
    ("host", "loopback"),
    [
        ("127.0.0.1", True),
        ("localhost", True),
        ("::1", True),
        ("0.0.0.0", False),
        ("example.com", False),
    ],
)
def test_loopback_detection(host, loopback):
    assert is_loopback(host) is loopback
