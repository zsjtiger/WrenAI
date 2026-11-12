"""Optional language-model client for draft suggestions.

Talks to any OpenAI-compatible ``/chat/completions`` endpoint (NVIDIA NIM,
OpenAI, a local server, ...). It is configured only by environment variables,
so no key is ever stored in a project:

* ``JANUS_LLM_BASE_URL``  e.g. ``https://integrate.api.nvidia.com/v1``
* ``JANUS_LLM_MODEL``     e.g. the model id served by that endpoint
* ``JANUS_LLM_API_KEY``   optional; sent as a bearer token when set

When either of the first two is missing, ``load_llm_config`` returns ``None``
and callers use their deterministic fallback. Any failure while calling the
model raises ``LlmError``; callers catch it and fall back as well.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_TIMEOUT_SECONDS = 60


class LlmError(RuntimeError):
    """The model could not be reached, refused, or returned unusable output."""


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS


def load_llm_config(environ: dict[str, str] | None = None) -> LlmConfig | None:
    """Read the configuration from the environment; ``None`` when not configured."""
    env = os.environ if environ is None else environ
    base_url = (env.get("JANUS_LLM_BASE_URL") or "").strip()
    model = (env.get("JANUS_LLM_MODEL") or "").strip()
    if not base_url or not model:
        return None
    return LlmConfig(
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=(env.get("JANUS_LLM_API_KEY") or "").strip() or None,
    )


def complete_json(config: LlmConfig, system: str, user: str) -> dict[str, Any]:
    """Ask the model for a JSON object and return it parsed.

    Raises ``LlmError`` on transport errors, non-2xx responses, and output that
    is not a JSON object. The API key is never included in an error message.
    """
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    body = {
        "model": config.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(
            f"{config.base_url}/chat/completions",
            headers=headers,
            json=body,
            timeout=config.timeout,
        )
    except requests.RequestException as exc:
        raise LlmError(f"model endpoint unreachable: {type(exc).__name__}") from exc
    if response.status_code >= 300:
        raise LlmError(f"model endpoint returned HTTP {response.status_code}")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LlmError("model response has no message content") from exc
    if not isinstance(content, str):
        raise LlmError("model message content is not text")

    try:
        parsed = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError as exc:
        raise LlmError("model did not return valid JSON") from exc
    if not isinstance(parsed, dict):
        raise LlmError("model did not return a JSON object")
    return parsed


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        return "\n".join(lines)
    return stripped
