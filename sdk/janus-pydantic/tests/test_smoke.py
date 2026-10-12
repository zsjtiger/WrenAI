"""Package skeleton smoke test — imports and exposes __version__."""

from __future__ import annotations


def test_package_imports():
    import janus_pydantic  # noqa: PLC0415

    assert isinstance(janus_pydantic.__version__, str)
    assert janus_pydantic.__version__
