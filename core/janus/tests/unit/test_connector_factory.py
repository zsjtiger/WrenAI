from __future__ import annotations

import pytest

from janus.connector import factory
from janus.model.data_source import DataSource
from janus.model.error import ErrorCode, JanusError

pytestmark = pytest.mark.unit


def test_connector_import_error_has_quoted_janusai_extra_hint(monkeypatch) -> None:
    def _fake_import_module(name: str):
        if name == "janus.connector.mysql":
            raise ImportError("No module named 'mysqlclient'")
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(factory.importlib, "import_module", _fake_import_module)

    with pytest.raises(JanusError) as exc:
        factory.get_connector(DataSource.doris, {})

    assert exc.value.error_code == ErrorCode.NOT_IMPLEMENTED
    assert "pip install 'janusai[mysql]'" in str(exc.value)
