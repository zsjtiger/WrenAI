"""Tests for MemoryProvider implementations."""

from unittest.mock import MagicMock, patch

import pytest

from janus_langchain._providers.memory import (
    LocalLanceDBMemoryProvider,
    NoopMemoryProvider,
)
from janus_langchain.exceptions import MemoryNotEnabledError


def test_noop_memory_provider_is_disabled():
    """NoopMemoryProvider reports as disabled and raises on open()."""
    provider = NoopMemoryProvider()

    assert provider.enabled is False

    with pytest.raises(MemoryNotEnabledError):
        provider.open()


def test_local_lancedb_provider_is_enabled(tmp_path):
    """A local provider is enabled (regardless of whether the dir exists yet)."""
    provider = LocalLanceDBMemoryProvider(memory_path=tmp_path / ".janus" / "memory")
    assert provider.enabled is True


def test_local_lancedb_provider_open_constructs_memory_store(tmp_path):
    """open() lazily constructs a janus.memory.MemoryStore at the given path."""
    memory_path = tmp_path / ".janus" / "memory"
    provider = LocalLanceDBMemoryProvider(memory_path=memory_path)

    fake_store = MagicMock(name="MemoryStore")
    with patch(
        "janus_langchain._providers.memory.MemoryStore",
        return_value=fake_store,
    ) as ctor:
        store = provider.open()

    assert store is fake_store
    ctor.assert_called_once_with(path=memory_path)
