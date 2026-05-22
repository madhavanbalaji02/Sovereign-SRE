"""
Tests for aws/pgvector/client.py and retriever.py

These tests use a mock PgVectorClient (no live Postgres needed).
For full integration, use testcontainers with a real pgvector image.
"""

import pytest


class MockPgVectorClient:
    """In-memory stub that mimics PgVectorClient for unit tests."""

    def __init__(self):
        self._store: list[dict] = []

    def upsert_embedding(self, file_path, chunk_index, content, embedding, metadata=None, language=None):
        # Replace if exists
        for i, row in enumerate(self._store):
            if row["file_path"] == file_path and row["chunk_index"] == chunk_index:
                self._store[i] = {
                    "file_path": file_path, "chunk_index": chunk_index,
                    "content": content, "embedding": embedding,
                    "metadata": metadata or {}, "language": language, "score": 1.0,
                }
                return
        self._store.append({
            "file_path": file_path, "chunk_index": chunk_index,
            "content": content, "embedding": embedding,
            "metadata": metadata or {}, "language": language, "score": 1.0,
        })

    def similarity_search(self, query_embedding, top_k=5, filter_language=None):
        results = self._store[:top_k]
        return results

    def delete_file_embeddings(self, file_path):
        self._store = [r for r in self._store if r["file_path"] != file_path]

    def health_check(self):
        return True

    def get_chunk_count(self):
        return len(self._store)


def test_upsert_and_search():
    client = MockPgVectorClient()
    embedding = [0.1] * 1024
    client.upsert_embedding("backend/main.py", 0, "def main(): pass", embedding,
                            metadata={"language": "python"}, language="python")

    results = client.similarity_search(embedding, top_k=5)
    assert len(results) == 1
    assert results[0]["file_path"] == "backend/main.py"
    assert results[0]["content"] == "def main(): pass"


def test_upsert_idempotent():
    client = MockPgVectorClient()
    emb = [0.2] * 1024
    client.upsert_embedding("a.py", 0, "v1", emb)
    client.upsert_embedding("a.py", 0, "v2", emb)
    assert client.get_chunk_count() == 1
    assert client._store[0]["content"] == "v2"


def test_delete_file():
    client = MockPgVectorClient()
    emb = [0.3] * 1024
    client.upsert_embedding("a.py", 0, "code", emb)
    client.upsert_embedding("b.py", 0, "more code", emb)
    client.delete_file_embeddings("a.py")
    assert client.get_chunk_count() == 1
    assert client._store[0]["file_path"] == "b.py"


def test_pgvector_retriever_uses_client(monkeypatch):
    """PgVectorRetriever._retrieve should call pg.similarity_search."""
    pytest.importorskip("llama_index", reason="llama_index not installed in this env")

    from llama_index.core.schema import QueryBundle

    mock_client = MockPgVectorClient()
    mock_client.upsert_embedding(
        "backend/api/main.py", 0, "FastAPI app entrypoint", [0.5] * 1024,
        language="python",
    )

    class FakeEmbed:
        def get_text_embedding(self, text):
            return [0.5] * 1024

    from aws.pgvector.retriever import PgVectorRetriever
    retriever = PgVectorRetriever(
        pg_client=mock_client,
        similarity_top_k=3,
        similarity_cutoff=0.0,
    )
    retriever._embed_model = FakeEmbed()

    nodes = retriever._retrieve(QueryBundle("FastAPI route handling"))
    assert len(nodes) >= 1
    assert nodes[0].node.metadata["file_path"] == "backend/api/main.py"
