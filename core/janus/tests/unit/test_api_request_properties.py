"""HTTP API: session properties in the request body, under the access rules."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from janus.api_server import build_app
from janus.engine import JanusEngine
from janus.mcp_server import ServeContext
from janus.model.data_source import DataSource
from tests.unit.conftest import manifest_b64, model_dict, shop_connection_info

pytestmark = pytest.mark.unit

TOKEN = "service-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def rls_project(make_project):
    customers = model_dict(
        "customers",
        "customers",
        [("id", "INTEGER"), ("name", "VARCHAR")],
        primary_key="id",
    )
    customers["rowLevelAccessControls"] = [
        {
            "name": "own_row",
            "requiredProperties": [{"name": "session_customer", "required": True}],
            "condition": "id = @session_customer",
        }
    ]
    return make_project([customers])


@pytest.fixture
def make_client(rls_project, shop_dir):
    engines = []

    def _make(token=TOKEN, fixed=None, trust=False):
        engine = JanusEngine(
            manifest_b64(rls_project),
            DataSource.duckdb,
            shop_connection_info(shop_dir),
            fallback=False,
        )
        engines.append(engine)
        ctx = ServeContext(
            project=rls_project,
            engine=engine,
            allow_write=False,
            no_connect=False,
            fixed_properties=fixed or {},
            protected_properties=frozenset({"session_customer"}),
            trust_client_properties=trust,
        )
        return TestClient(build_app(ctx, token=token))

    yield _make
    for engine in engines:
        engine.close()


def _plan(client, props, headers=None):
    return client.post(
        "/dry-plan",
        json={"sql": "SELECT id FROM customers", "properties": props},
        headers=headers or {},
    )


def test_token_holder_passes_the_access_property(make_client):
    r = _plan(make_client(), {"session_customer": 7}, AUTH)
    assert r.status_code == 200, r.text
    assert "= 7" in r.json()["sql"]


def test_without_token_the_access_property_is_refused(make_client):
    r = _plan(make_client(token=None), {"session_customer": 7})
    assert r.status_code == 400
    assert "set by the server" in r.json()["error"]


def test_without_token_the_operator_can_opt_in(make_client):
    r = _plan(make_client(token=None, trust=True), {"session_customer": 7})
    assert r.status_code == 200, r.text


def test_server_fixed_value_cannot_be_overridden(make_client):
    r = _plan(make_client(fixed={"session_customer": 7}), {"session_customer": 8}, AUTH)
    assert r.status_code == 400


def test_properties_must_be_an_object(make_client):
    r = _plan(make_client(), ["session_customer"], AUTH)
    assert r.status_code == 400
    assert "'properties' must be an object" in r.json()["error"]
