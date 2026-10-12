"""Memory providers resolve where the long-lived context store lives.

v0.1 ships:
  - ``LocalLanceDBMemoryProvider``: opens a ``MemoryStore`` against a local
    ``.janus/memory/`` directory.
  - ``NoopMemoryProvider``: signals that memory is disabled. Direct API calls
    raise ``MemoryNotEnabledError``; LLM-facing tools are filtered out.

Auto-selection is performed by ``JanusToolkit.from_project`` based on whether
``<project>/.janus/memory/`` exists.
"""

from pathlib import Path

from janus.memory.store import MemoryStore

from janus_pydantic.exceptions import MemoryNotEnabledError


class LocalLanceDBMemoryProvider:
    """Lazily opens a local LanceDB-backed ``MemoryStore`` on first use."""

    enabled = True

    def __init__(self, *, memory_path: Path):
        self._memory_path = memory_path

    def open(self) -> MemoryStore:
        return MemoryStore(path=self._memory_path)


class NoopMemoryProvider:
    """Inert provider used when no ``.janus/memory/`` exists in the project."""

    enabled = False

    def open(self) -> MemoryStore:
        raise MemoryNotEnabledError(
            "memory is not enabled for this toolkit. "
            "Run `janus memory index` in your project to enable it."
        )
