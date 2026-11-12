"""API embedding backend: client behavior, backend selection, store and fallback.

A real local HTTP server stands in for an OpenAI-compatible /embeddings
endpoint. Its vectors are a hashed bag of words, so texts that share words
land near each other and recall results mean something.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from janus.memory.api_embeddings import (
    ApiEmbeddingConfig,
    ApiEmbeddings,
    EmbeddingApiError,
    load_api_embedding_config,
)
from janus.memory.embeddings import API_BACKEND, resolve_embedding_backend

pytestmark = pytest.mark.unit

DIM = 16


def _vector(text: str) -> list[float]:
    vec = [0.0] * DIM
    for word in text.lower().split():
        bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIM
        vec[bucket] += 1.0
    return vec


class _Endpoint:
    """Serves /embeddings; can be told to fail, or to answer out of order."""

    def __init__(self) -> None:
        self.status = 200
        self.reverse_order = False
        self.drop_last = False
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - http.server API
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                endpoint.requests.append(body)
                endpoint.headers.append(dict(self.headers))
                if endpoint.status >= 300:
                    payload = b'{"error": "down"}'
                else:
                    items = [
                        {"index": i, "embedding": _vector(text)}
                        for i, text in enumerate(body["input"])
                    ]
                    if endpoint.reverse_order:
                        items.reverse()
                    if endpoint.drop_last:
                        items = items[:-1]
                    payload = json.dumps({"data": items}).encode()
                self.send_response(endpoint.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}/v1"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()

    def config(self, *, api_key=None, asymmetric=False) -> ApiEmbeddingConfig:
        return ApiEmbeddingConfig(
            base_url=self.url,
            model="embed-test",
            api_key=api_key,
            asymmetric=asymmetric,
            timeout=5,
        )


@pytest.fixture
def endpoint():
    with _Endpoint() as server:
        yield server


@pytest.fixture
def api_env(monkeypatch, endpoint):
    """Point the environment at the test endpoint and force the API backend."""
    monkeypatch.setenv("JANUS_EMBEDDING_BACKEND", "api")
    monkeypatch.setenv("JANUS_EMBEDDING_API_BASE_URL", endpoint.url)
    monkeypatch.setenv("JANUS_EMBEDDING_API_MODEL", "embed-test")
    monkeypatch.delenv("JANUS_EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("JANUS_EMBEDDING_API_ASYMMETRIC", raising=False)
    return endpoint


# ── configuration and selection ──────────────────────────────────────────────


def test_configuration_needs_both_url_and_model():
    assert load_api_embedding_config({}) is None
    assert (
        load_api_embedding_config({"JANUS_EMBEDDING_API_BASE_URL": "http://x"}) is None
    )
    cfg = load_api_embedding_config(
        {
            "JANUS_EMBEDDING_API_BASE_URL": "https://e.test/v1/",
            "JANUS_EMBEDDING_API_MODEL": "m",
            "JANUS_EMBEDDING_API_KEY": "k",
            "JANUS_EMBEDDING_API_ASYMMETRIC": "true",
        }
    )
    assert cfg == ApiEmbeddingConfig(
        base_url="https://e.test/v1", model="m", api_key="k", asymmetric=True
    )


def test_api_backend_is_selected_when_configured(api_env):
    assert resolve_embedding_backend() == API_BACKEND


def test_requesting_api_without_configuration_falls_back(monkeypatch):
    monkeypatch.setenv("JANUS_EMBEDDING_BACKEND", "api")
    monkeypatch.delenv("JANUS_EMBEDDING_API_BASE_URL", raising=False)
    monkeypatch.delenv("JANUS_EMBEDDING_API_MODEL", raising=False)
    assert resolve_embedding_backend() != API_BACKEND


# ── the client ───────────────────────────────────────────────────────────────


def test_source_vectors_are_normalized_and_in_input_order(endpoint):
    endpoint.reverse_order = True  # the server answers out of order
    emb = ApiEmbeddings(endpoint.config())
    texts = ["monthly revenue", "customer count", "order status"]
    vectors = emb.compute_source_embeddings(texts)

    assert len(vectors) == 3
    for text, vec in zip(texts, vectors, strict=True):
        assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0, rel_tol=1e-6)
        expected = _vector(text)
        norm = math.sqrt(sum(x * x for x in expected))
        assert [round(x, 6) for x in vec] == [round(x / norm, 6) for x in expected]


def test_inputs_are_sent_in_batches(endpoint):
    emb = ApiEmbeddings(endpoint.config())
    emb.compute_source_embeddings([f"text {i}" for i in range(150)])
    sizes = [len(body["input"]) for body in endpoint.requests]
    assert sizes == [64, 64, 22]


def test_asymmetric_endpoints_get_passage_and_query_roles(endpoint):
    ApiEmbeddings(endpoint.config(asymmetric=True)).compute_source_embeddings(["a"])
    ApiEmbeddings(endpoint.config(asymmetric=True)).compute_query_embeddings("q")
    assert endpoint.requests[0]["input_type"] == "passage"
    assert endpoint.requests[1]["input_type"] == "query"


def test_input_type_is_absent_for_symmetric_endpoints(endpoint):
    ApiEmbeddings(endpoint.config()).compute_source_embeddings(["a"])
    ApiEmbeddings(endpoint.config()).compute_query_embeddings("q")
    assert all("input_type" not in body for body in endpoint.requests)


def test_bearer_key_is_sent_and_never_echoed_in_errors(endpoint):
    endpoint.status = 401
    emb = ApiEmbeddings(endpoint.config(api_key="super-secret"))
    with pytest.raises(EmbeddingApiError, match="HTTP 401") as exc:
        emb.compute_source_embeddings(["a"])
    assert "super-secret" not in str(exc.value)

    endpoint.status = 200
    ApiEmbeddings(endpoint.config(api_key="super-secret")).compute_source_embeddings(
        ["a"]
    )
    assert endpoint.headers[-1]["Authorization"] == "Bearer super-secret"


def test_server_error_raises(endpoint):
    endpoint.status = 503
    with pytest.raises(EmbeddingApiError, match="HTTP 503"):
        ApiEmbeddings(endpoint.config()).compute_query_embeddings("q")


def test_short_reply_is_rejected(endpoint):
    endpoint.drop_last = True
    with pytest.raises(EmbeddingApiError, match="2 vectors for 3 inputs"):
        ApiEmbeddings(endpoint.config()).compute_source_embeddings(["a", "b", "c"])


def test_unreachable_endpoint_raises():
    cfg = ApiEmbeddingConfig(base_url="http://127.0.0.1:1/v1", model="m", timeout=2)
    with pytest.raises(EmbeddingApiError, match="unreachable"):
        ApiEmbeddings(cfg).compute_source_embeddings(["a"])


# ── store and recall, end to end ─────────────────────────────────────────────


@pytest.fixture
def store(tmp_path, api_env):
    pytest.importorskip("lancedb")
    from janus.memory.store import MemoryStore  # noqa: PLC0415

    return MemoryStore(path=str(tmp_path / "memory"))


def test_store_recalls_by_meaning_through_the_api(store):
    store.store_query("total revenue by month", "SELECT month, sum(amount) FROM orders")
    store.store_query("how many customers signed up", "SELECT count(*) FROM customers")

    hits = store.recall_queries("monthly revenue total", limit=1)
    assert hits and "revenue" in hits[0]["nl_query"]


def test_recall_falls_back_to_keyword_search_when_the_endpoint_fails(
    store, endpoint, tmp_path
):
    from janus.memory.index_backend import LanceDBIndex  # noqa: PLC0415
    from janus.memory.markdown import write_query_markdown  # noqa: PLC0415

    project = tmp_path / "project"
    write_query_markdown(project, "total revenue by month", "SELECT 1")
    store.store_query("total revenue by month", "SELECT 1")

    endpoint.status = 500  # the endpoint goes down after indexing
    index = LanceDBIndex(project, str(tmp_path / "memory"))
    hits = index.search("revenue", limit=3)

    assert hits, "keyword fallback should still find the stored pair"
    assert any("revenue" in str(h).lower() for h in hits)


def test_indexing_fails_loudly_when_the_endpoint_is_down(store, endpoint):
    endpoint.status = 500
    with pytest.raises(EmbeddingApiError):
        store.store_query("total revenue", "SELECT 1")
