"""
pgvector LlamaIndex Retriever
==============================
Implements LlamaIndex BaseRetriever backed by pgvector.
Drop-in replacement for ChromaDB retriever in query_engine.py.
"""

import os
from typing import List, Optional

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from aws.pgvector.client import PgVectorClient

EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")


class PgVectorRetriever(BaseRetriever):
    """
    LlamaIndex-compatible retriever that queries pgvector.
    """

    def __init__(
        self,
        pg_client: Optional[PgVectorClient] = None,
        embed_model_name: str = EMBED_MODEL,
        similarity_top_k: int = 5,
        similarity_cutoff: float = 0.3,
    ):
        self._pg = pg_client or PgVectorClient()
        self._embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
        self._top_k = similarity_top_k
        self._cutoff = similarity_cutoff
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        query_text = query_bundle.query_str

        # Embed the query with BGE-M3 (same model used at indexing time)
        embedding = self._embed_model.get_text_embedding(query_text)

        # Query pgvector
        results = self._pg.similarity_search(
            query_embedding=embedding,
            top_k=self._top_k,
        )

        nodes_with_scores = []
        for r in results:
            score = r["score"]
            if score < self._cutoff:
                continue
            node = TextNode(
                text=r["content"],
                metadata={
                    "file_path": r["file_path"],
                    "file_name": r["file_path"].split("/")[-1],
                    "language": r.get("language", ""),
                    "chunk_index": r.get("chunk_index", 0),
                    **r.get("metadata", {}),
                },
            )
            nodes_with_scores.append(NodeWithScore(node=node, score=score))

        return nodes_with_scores
