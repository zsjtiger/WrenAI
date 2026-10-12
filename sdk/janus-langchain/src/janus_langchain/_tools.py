"""LangChain tool wrappers exposing toolkit operations to LLMs.

Each tool returns a JSON-serializable envelope: success or error.
On error, the envelope's ``ok=False`` allows the agent to inspect ``error.phase``
and ``error.code`` to recover. Set ``raise_on_error=True`` on get_tools() to
raise instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

from janus_langchain._envelope import make_error, make_success
from janus_langchain._format import (
    format_dry_plan_content,
    format_list_models_content,
    format_query_content,
)

if TYPE_CHECKING:
    from janus_langchain._toolkit import JanusToolkit


# Hard cap for the LLM-facing `janus_query` tool. The 16 KB content cap
# already truncates the rendered preview, but `data.rows` materializes every
# row via `to_pylist()` — a runaway `limit` value (typo, hallucinated huge
# number) would still balloon memory before that cap fires. 1000 rows leaves
# headroom over the 100-default while keeping payloads bounded. Direct API
# (`toolkit.query`) keeps no cap on purpose; that's a Python-programmer surface.
MAX_QUERY_ROWS = 1000


def build_runtime_tools(toolkit: JanusToolkit, *, raise_on_error: bool) -> list:
    """Return janus_query, janus_dry_plan, janus_list_models bound to toolkit."""
    return [
        _build_janus_query(toolkit, raise_on_error=raise_on_error),
        _build_janus_dry_plan(toolkit, raise_on_error=raise_on_error),
        _build_janus_list_models(toolkit, raise_on_error=raise_on_error),
    ]


def _build_janus_query(toolkit: JanusToolkit, *, raise_on_error: bool):
    @tool("janus_query")
    def janus_query(sql: str, limit: int = 100) -> dict[str, Any]:
        """Execute SQL through the Janus semantic layer and return rows.

        Use this after janus_dry_plan looks correct. Default limit is 100 rows;
        increase only when you need more. Hard cap is 1000 rows — beyond that,
        aggregate in SQL instead.
        """
        if limit < 1 or limit > MAX_QUERY_ROWS:
            err = ValueError(
                f"limit must be between 1 and {MAX_QUERY_ROWS} (got {limit}). "
                "Aggregate in SQL if you need more rows."
            )
            if raise_on_error:
                raise err
            return make_error(err)

        try:
            table = toolkit.query(sql, limit=limit)
        except Exception as exc:
            if raise_on_error:
                raise
            return make_error(exc)

        content, warnings = format_query_content(table, total_rows=table.num_rows)
        data = {
            "columns": table.column_names,
            "rows": table.to_pylist(),
            "row_count": table.num_rows,
            "content_truncated": bool(warnings),
        }
        return make_success(content=content, data=data, warnings=warnings)

    return janus_query


def _build_janus_dry_plan(toolkit: JanusToolkit, *, raise_on_error: bool):
    @tool("janus_dry_plan")
    def janus_dry_plan(sql: str) -> dict[str, Any]:
        """Plan SQL through MDL and return the expanded target-dialect SQL.

        Use this to verify your SQL targets Janus models correctly before
        running janus_query. Cheap (no DB round-trip).
        """
        try:
            dialect_sql = toolkit.dry_plan(sql)
        except Exception as exc:
            if raise_on_error:
                raise
            return make_error(exc)

        return make_success(
            content=format_dry_plan_content(dialect_sql),
            data={"dialect_sql": dialect_sql},
        )

    return janus_dry_plan


def _build_janus_list_models(toolkit: JanusToolkit, *, raise_on_error: bool):
    @tool("janus_list_models")
    def janus_list_models() -> dict[str, Any]:
        """List all models defined in this Janus project with column counts and descriptions."""
        try:
            manifest = toolkit._mdl_source.load_manifest()
        except Exception as exc:
            if raise_on_error:
                raise
            return make_error(exc)

        return make_success(
            content=format_list_models_content(manifest),
            data={"models": manifest.get("models", []) or []},
        )

    return janus_list_models
