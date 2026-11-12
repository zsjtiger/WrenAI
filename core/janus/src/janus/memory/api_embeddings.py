"""Embeddings from an OpenAI-compatible ``/embeddings`` endpoint.

Selected with ``JANUS_EMBEDDING_BACKEND=api``. Configuration is environment
only, so no key is ever written into a project or a store:

* ``JANUS_EMBEDDING_API_BASE_URL``  e.g. ``https://integrate.api.nvidia.com/v1``
* ``JANUS_EMBEDDING_API_MODEL``     the embedding model id served by that endpoint
* ``JANUS_EMBEDDING_API_KEY``       optional; sent as a bearer token when set
* ``JANUS_EMBEDDING_API_ASYMMETRIC`` optional (``1``/``true``). Some endpoints,
  NVIDIA's among them, embed documents and queries differently and need an
  ``input_type``: ``passage`` for indexed text and ``query`` for questions. When
  set, that is sent; otherwise no ``input_type`` is sent.

Vectors are L2-normalized, as the local backends produce them, so distance
ranking in a store stays consistent. The vector dimension is whatever the model
returns; ``MemoryStore`` already rejects a dimension that differs from the store.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any

import requests

BATCH_SIZE = 64
DEFAULT_TIMEOUT_SECONDS = 60
_TRUTHY = {"1", "true", "yes", "on"}


class EmbeddingApiError(RuntimeError):
    """The embedding endpoint could not be reached or returned unusable vectors."""


@dataclass(frozen=True)
class ApiEmbeddingConfig:
    base_url: str
    model: str
    api_key: str | None = None
    asymmetric: bool = False
    timeout: float = DEFAULT_TIMEOUT_SECONDS


def load_api_embedding_config(
    environ: dict[str, str] | None = None,
) -> ApiEmbeddingConfig | None:
    """Read the configuration from the environment; ``None`` when incomplete."""
    env = os.environ if environ is None else environ
    base_url = (env.get("JANUS_EMBEDDING_API_BASE_URL") or "").strip()
    model = (env.get("JANUS_EMBEDDING_API_MODEL") or "").strip()
    if not base_url or not model:
        return None
    asymmetric = (env.get("JANUS_EMBEDDING_API_ASYMMETRIC") or "").strip().lower()
    return ApiEmbeddingConfig(
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=(env.get("JANUS_EMBEDDING_API_KEY") or "").strip() or None,
        asymmetric=asymmetric in _TRUTHY,
    )


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0.0:
        return vector
    return [x / norm for x in vector]


class ApiEmbeddings:
    """Embedding function backed by an HTTP endpoint.

    Implements the ``compute_source_embeddings`` / ``compute_query_embeddings``
    pair that ``MemoryStore`` calls, like the local backends.
    """

    def __init__(self, config: ApiEmbeddingConfig):
        self._config = config

    def _post(self, inputs: list[str], role: str) -> list[list[float]]:
        cfg = self._config
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        body: dict[str, Any] = {"model": cfg.model, "input": inputs}
        if cfg.asymmetric:
            body["input_type"] = role
        try:
            response = requests.post(
                f"{cfg.base_url}/embeddings",
                headers=headers,
                json=body,
                timeout=cfg.timeout,
            )
        except requests.RequestException as exc:
            raise EmbeddingApiError(
                f"embedding endpoint unreachable: {type(exc).__name__}"
            ) from exc
        if response.status_code >= 300:
            raise EmbeddingApiError(
                f"embedding endpoint returned HTTP {response.status_code}"
            )
        try:
            data = response.json()["data"]
            items = sorted(data, key=lambda item: item["index"])
            vectors = [[float(x) for x in item["embedding"]] for item in items]
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingApiError(
                "embedding reply is not in the expected shape"
            ) from exc
        if len(vectors) != len(inputs):
            raise EmbeddingApiError(
                f"embedding reply has {len(vectors)} vectors for {len(inputs)} inputs"
            )
        return vectors

    def _encode(self, texts: list[str], role: str) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._post(texts[start : start + BATCH_SIZE], role))
        dims = {len(v) for v in vectors}
        if len(dims) != 1 or 0 in dims:
            raise EmbeddingApiError(
                f"embedding vectors have inconsistent sizes: {dims}"
            )
        return [_normalize(v) for v in vectors]

    def compute_source_embeddings(self, texts) -> list:
        """Embed documents for indexing."""
        return self._encode(list(texts), "passage")

    def compute_query_embeddings(self, query) -> list:
        """Embed one query string, or a batch of them."""
        queries = [query] if isinstance(query, str) else list(query)
        return self._encode(queries, "query")
