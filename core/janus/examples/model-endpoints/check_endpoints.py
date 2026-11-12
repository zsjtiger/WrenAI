"""Check the embedding endpoint and the chat model that janus will use.

Reads the JANUS_EMBEDDING_* and JANUS_LLM_* variables (a .env file in this
directory is loaded if present). Prints results without ever printing a key.

    python check_endpoints.py

Exit code 0 when both checks pass, 1 otherwise.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.split("  #", 1)[0].strip()
        os.environ.setdefault(key.strip(), value)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def check_embeddings() -> bool:
    from janus.memory.api_embeddings import (  # noqa: PLC0415
        ApiEmbeddings,
        EmbeddingApiError,
        load_api_embedding_config,
    )

    cfg = load_api_embedding_config()
    if cfg is None:
        print(
            "embeddings: not configured (set JANUS_EMBEDDING_API_BASE_URL and _MODEL)"
        )
        return False
    print(f"embeddings: {cfg.base_url}  model={cfg.model}")
    try:
        vectors = ApiEmbeddings(cfg).compute_source_embeddings(
            ["你好，世界", "hello world"]
        )
    except EmbeddingApiError as exc:
        print(f"  FAILED: {exc}")
        return False
    print(f"  got {len(vectors)} vectors, dimension {len(vectors[0])}")
    print(f"  cosine(你好，世界, hello world) = {_cosine(vectors[0], vectors[1]):.3f}")
    return True


def check_chat() -> bool:
    from janus.llm import LlmError, complete_json, load_llm_config  # noqa: PLC0415

    cfg = load_llm_config()
    if cfg is None:
        print("chat model: not configured (set JANUS_LLM_BASE_URL and JANUS_LLM_MODEL)")
        return False
    key_state = "key set" if cfg.api_key else "no key"
    print(f"chat model: {cfg.base_url}  model={cfg.model}  ({key_state})")
    try:
        reply = complete_json(
            cfg,
            'Reply with a JSON object {"ok": true, "model_said": "<your model name>"} and nothing else.',
            "ping",
        )
    except LlmError as exc:
        print(f"  FAILED: {exc}")
        return False
    print(f"  reply: {reply}")
    return reply.get("ok") is True


def main() -> int:
    _load_dotenv(Path(__file__).resolve().parent / ".env")
    emb_ok = check_embeddings()
    print()
    chat_ok = check_chat()
    print()
    print(
        f"embeddings {'OK' if emb_ok else 'FAILED'}; chat model {'OK' if chat_ok else 'FAILED'}"
    )
    return 0 if emb_ok and chat_ok else 1


if __name__ == "__main__":
    sys.exit(main())
