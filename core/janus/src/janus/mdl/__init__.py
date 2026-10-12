"""MDL processing utilities backed by janus-core-py."""

from functools import lru_cache

import janus_core


@lru_cache(maxsize=32)
def get_session_context(
    manifest_str: str | None,
    function_path: str | None,
    properties: frozenset | None = None,
    data_source: str | None = None,
) -> janus_core.SessionContext:
    """Build (or reuse) a SessionContext for the given manifest tuple.

    Bounded LRU: the cache key includes the per-query extracted manifest
    (engine.py ``extract_by``), so an unbounded cache would grow one
    SessionContext per distinct table subset for the life of the process.
    """
    return janus_core.SessionContext(
        manifest_str, function_path, properties, data_source
    )


def get_manifest_extractor(manifest_str: str) -> janus_core.ManifestExtractor:
    return janus_core.ManifestExtractor(manifest_str)


def to_json_base64(manifest) -> str:
    return janus_core.to_json_base64(manifest)


def transform_sql(
    manifest_str: str,
    sql: str,
    data_source: str | None = None,
    function_path: str | None = None,
    properties: dict | None = None,
) -> str:
    """Transform SQL through janus-core MDL processing.

    Returns the planned SQL string (dialect-neutral DataFusion SQL).
    """
    processed = None
    if properties:
        processed = frozenset(properties.items())

    session = get_session_context(manifest_str, function_path, processed, data_source)
    return session.transform_sql(sql)
