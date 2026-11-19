"""MVP: answer a business question over the Janus HTTP API.

Flow for one question:

1. Read the certified models and their columns from Janus, with the caller's token.
2. Ask an LLM (OpenAI-compatible, configured by JANUS_LLM_BASE_URL and
   JANUS_LLM_MODEL) for one SELECT over those models.
3. Run it through Janus /query with the same token, so the row and column rules
   of the caller's role apply. Janus returns the rows, the expanded SQL, and the
   provenance (models used, the role, where each property came from).

The app never reads data itself and never runs SQL that Janus has not planned.
Only SELECT statements are accepted.

Run:
    JANUS_URL=http://127.0.0.1:8090 JANUS_LLM_BASE_URL=... JANUS_LLM_MODEL=... \\
        python qa_app.py            # serves POST /ask on port 8100
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable

import requests

from janus.llm import LlmConfig, LlmError, complete_json, load_llm_config

ANSWER_SYSTEM = (
    "You write one SQL SELECT for a semantic layer. Use only the model and column "
    "names you are given; write the SQL against model names, not database tables. "
    'Reply with a JSON object {"sql": "<one SELECT>"} and nothing else. '
    'If the question cannot be answered from these models, reply {"sql": null}.'
)

_SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE)


class QaError(RuntimeError):
    """The question could not be answered. ``status`` is the HTTP status to return."""

    def __init__(self, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.status = status


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def fetch_schema(janus_url: str, token: str | None, http: Any = requests) -> list[dict]:
    """The certified models and their columns, as the caller may see them."""
    base = janus_url.rstrip("/")
    listing = http.get(f"{base}/models", headers=_headers(token), timeout=30)
    if listing.status_code != 200:
        raise QaError(
            f"Janus refused the model list ({listing.status_code})", listing.status_code
        )
    models = []
    for item in listing.json().get("models", []):
        if not item.get("certified"):
            continue
        detail = http.get(
            f"{base}/models/{item['name']}", headers=_headers(token), timeout=30
        )
        if detail.status_code == 200:
            models.append(detail.json())
    if not models:
        raise QaError("no certified models are available to this caller", 404)
    return models


def build_context(models: list[dict]) -> str:
    """The schema, as plain text for the LLM."""
    lines = []
    for model in models:
        cols = ", ".join(
            f"{c['name']} {c.get('type') or ''}".rstrip() for c in model["columns"]
        )
        pk = (
            f" (primary key: {model['primary_key']})"
            if model.get("primary_key")
            else ""
        )
        lines.append(f"- {model['name']}{pk}: {cols}")
    return "\n".join(lines)


def draft_sql(llm: LlmConfig, question: str, context: str) -> str:
    """One SELECT that answers the question, or raise QaError."""
    try:
        reply = complete_json(
            llm, ANSWER_SYSTEM, f"Models:\n{context}\n\nQuestion: {question}"
        )
    except LlmError as exc:
        raise QaError(f"the model could not draft SQL: {exc}", 503) from exc
    sql = reply.get("sql") if isinstance(reply, dict) else None
    if not isinstance(sql, str) or not sql.strip():
        raise QaError("the question cannot be answered from the certified models", 422)
    sql = sql.strip().rstrip(";")
    if ";" in sql or not _SELECT_ONLY.match(sql):
        raise QaError("only a single SELECT statement is accepted", 422)
    return sql


def run_query(
    janus_url: str,
    token: str | None,
    sql: str,
    *,
    limit: int = 100,
    http: Any = requests,
) -> dict:
    """Run the SQL through Janus, so the caller's role applies."""
    response = http.post(
        f"{janus_url.rstrip('/')}/query",
        json={"sql": sql, "limit": limit, "include_sql": True},
        headers=_headers(token),
        timeout=60,
    )
    body = response.json() if response.content else {}
    if response.status_code != 200:
        raise QaError(
            body.get("error", "Janus refused the query"), response.status_code
        )
    return body


def answer(
    question: str,
    *,
    janus_url: str,
    token: str | None,
    llm: LlmConfig,
    http: Any = requests,
    draft: Callable[[LlmConfig, str, str], str] | None = None,
    limit: int = 100,
) -> dict:
    """Answer one question. Returns the SQL, the rows, and the provenance."""
    if not question or not question.strip():
        raise QaError("the question is empty", 400)
    # Looked up at call time, so a replacement of draft_sql is picked up.
    draft = draft or draft_sql
    models = fetch_schema(janus_url, token, http)
    sql = draft(llm, question.strip(), build_context(models))
    result = run_query(janus_url, token, sql, limit=limit, http=http)
    return {
        "question": question.strip(),
        "sql": sql,
        "expanded_sql": result.get("provenance", {}).get("expanded_sql"),
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "row_count": result.get("row_count", 0),
        "truncated": result.get("truncated", False),
        "provenance": result.get("provenance", {}),
    }


def build_app(*, janus_url: str, llm: LlmConfig, http: Any = requests):
    """The HTTP wrapper: POST /ask {"question": "..."} with the caller's Bearer token."""
    from starlette.applications import Starlette  # noqa: PLC0415
    from starlette.requests import Request  # noqa: PLC0415
    from starlette.responses import JSONResponse  # noqa: PLC0415
    from starlette.routing import Route  # noqa: PLC0415

    async def ask(request: Request):
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else None
        if token is None:
            return JSONResponse({"error": "missing bearer token"}, status_code=401)
        try:
            body = await request.json()
        except ValueError:
            body = {}
        question = body.get("question", "") if isinstance(body, dict) else ""
        try:
            result = answer(
                question if isinstance(question, str) else "",
                janus_url=janus_url,
                token=token,
                llm=llm,
                http=http,
            )
        except QaError as exc:
            return JSONResponse({"error": str(exc)}, status_code=exc.status)
        return JSONResponse(result)

    return Starlette(routes=[Route("/ask", ask, methods=["POST"])])


def main() -> None:
    import uvicorn  # noqa: PLC0415

    llm = load_llm_config(dict(os.environ))
    if llm is None:
        raise SystemExit("set JANUS_LLM_BASE_URL and JANUS_LLM_MODEL to draft SQL")
    janus_url = os.environ.get("JANUS_URL", "http://127.0.0.1:8090")
    uvicorn.run(build_app(janus_url=janus_url, llm=llm), host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()
