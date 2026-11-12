"""``require_certified``: config loading and engine enforcement.

Planning only (dry_plan) — no database is opened. The engine is built from a
manifest whose model either carries ``certified: true`` or does not, and the
config flag is toggled around it.
"""

from __future__ import annotations

import base64
import copy

import orjson
import pytest

from janus import JanusEngine
from janus.config import JanusConfig, load_config
from janus.model.data_source import DataSource
from janus.model.error import ErrorCode, JanusError

pytestmark = pytest.mark.unit

_BASE_MODEL = {
    "name": "orders",
    "tableReference": {"schema": "main", "table": "orders"},
    "columns": [
        {"name": "o_orderkey", "type": "integer"},
        {"name": "o_totalprice", "type": "double"},
    ],
    "primaryKey": "o_orderkey",
}


def _manifest_b64(certified: object | None) -> str:
    model = copy.deepcopy(_BASE_MODEL)
    if certified is not None:
        model["properties"] = {"certified": certified}
    manifest = {"catalog": "janus", "schema": "public", "models": [model]}
    return base64.b64encode(orjson.dumps(manifest)).decode()


def _engine(tmp_path, *, certified: object | None, require: bool) -> JanusEngine:
    conn_info = {"url": str(tmp_path), "format": "duckdb"}
    return JanusEngine(
        _manifest_b64(certified),
        DataSource.duckdb,
        conn_info,
        fallback=False,
        config=JanusConfig(require_certified=require),
    )


_QUERY = 'SELECT o_orderkey FROM "orders" LIMIT 1'


# ── config ────────────────────────────────────────────────────────────────────


def test_require_certified_defaults_to_off(tmp_path) -> None:
    assert load_config(tmp_path).require_certified is False


def test_require_certified_is_read_from_config_json(tmp_path) -> None:
    (tmp_path / "config.json").write_text('{"require_certified": true}')
    assert load_config(tmp_path).require_certified is True


def test_require_certified_must_be_a_boolean(tmp_path) -> None:
    (tmp_path / "config.json").write_text('{"require_certified": "yes"}')
    with pytest.raises(JanusError) as exc:
        load_config(tmp_path)
    assert exc.value.code == ErrorCode.GENERIC_USER_ERROR
    assert "require_certified" in str(exc.value)


# ── engine ────────────────────────────────────────────────────────────────────


def test_flag_off_plans_an_uncertified_model(tmp_path) -> None:
    with _engine(tmp_path, certified=None, require=False) as engine:
        assert "orders" in engine.dry_plan(_QUERY)


def test_flag_on_refuses_an_uncertified_model(tmp_path) -> None:
    with _engine(tmp_path, certified=None, require=True) as engine:
        with pytest.raises(JanusError) as exc:
            engine.dry_plan(_QUERY)
    assert "model 'orders' is not certified" in str(exc.value)


def test_flag_on_refuses_a_model_marked_not_certified(tmp_path) -> None:
    with _engine(tmp_path, certified=False, require=True) as engine:
        with pytest.raises(JanusError, match="not certified"):
            engine.dry_plan(_QUERY)


def test_flag_on_plans_a_certified_model(tmp_path) -> None:
    with _engine(tmp_path, certified=True, require=True) as engine:
        assert "orders" in engine.dry_plan(_QUERY)
