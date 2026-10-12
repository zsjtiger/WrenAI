"""Tests for SDK-specific exception types."""

import pytest

from janus_langchain.exceptions import (
    MemoryNotEnabledError,
    JanusToolkitInitError,
)


def test_janus_toolkit_init_error_carries_message():
    with pytest.raises(JanusToolkitInitError, match="missing target/mdl.json"):
        raise JanusToolkitInitError("missing target/mdl.json")


def test_memory_not_enabled_error_is_distinct_type():
    """MemoryNotEnabledError is its own class, not a generic ValueError."""
    err = MemoryNotEnabledError("memory provider not configured")
    assert isinstance(err, MemoryNotEnabledError)
    assert isinstance(err, Exception)
    assert "memory provider" in str(err)
