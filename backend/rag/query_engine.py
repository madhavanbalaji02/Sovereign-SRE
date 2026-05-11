"""
Query Engine
============
LlamaIndex query engine for asking questions about the codebase.
"""

import os
from typing import Optional

from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.llms.groq import Groq as LlamaGroq
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# =============================================================================
# CONFIGURATION
# =============================================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://localhost:8000")
LLM_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "sovereign_sre_codebase")


# =============================================================================
# QUERY ENGINE FACTORY
# =============================================================================

def create_query_engine(
    collection_name: str = COLLECTION_NAME,
    chroma_host: str = CHROMA_HOST,
    llm_model: str = LLM_MODEL,
    embed_model: str = EMBED_MODEL,
    similarity_top_k: int = 5,
    similarity_cutoff: float = 0.5,
) -> RetrieverQueryEngine:
    """
    Create a query engine for the codebase.

    Args:
        collection_name: ChromaDB collection name
        chroma_host: ChromaDB API URL
        llm_model: Grok model name for response generation
        embed_model: HuggingFace embedding model name
        similarity_top_k: Number of similar chunks to retrieve
        similarity_cutoff: Minimum similarity score

    Returns:
        Configured query engine
    """
    # Configure LLM (Groq cloud — Llama 3.3 on LPU)
    llm = LlamaGroq(
        model=llm_model,
        api_key=GROQ_API_KEY,
    )
    Settings.llm = llm

    # Configure embeddings (local HuggingFace, no API key needed)
    embed = HuggingFaceEmbedding(model_name=embed_model)
    Settings.embed_model = embed
    
    # Connect to ChromaDB — ephemeral (in-memory) for HF Spaces demo, HTTP otherwise
    if os.environ.get("CHROMA_MODE") == "ephemeral":
        chroma_client = chromadb.EphemeralClient()
    else:
        host = chroma_host.replace("http://", "").replace("https://", "")
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 8000
        chroma_client = chromadb.HttpClient(host=host, port=port)

    collection = chroma_client.get_or_create_collection(name=collection_name)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    
    # Create index from vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embed,
    )
    
    # Create retriever
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=similarity_top_k,
    )
    
    # Create query engine
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[
            SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)
        ],
    )
    
    return query_engine


# =============================================================================
# QUERY FUNCTION
# =============================================================================

async def query_codebase(
    query: str,
    query_engine: Optional[RetrieverQueryEngine] = None,
) -> dict:
    """
    Query the codebase and return a structured response.
    
    Args:
        query: Natural language question about the codebase
        query_engine: Optional pre-configured query engine
        
    Returns:
        Dictionary with response, sources, and metadata
    """
    if query_engine is None:
        query_engine = create_query_engine()
    
    # Execute query
    response = query_engine.query(query)
    
    # Extract source information
    sources = []
    for node in response.source_nodes:
        sources.append({
            "file_path": node.metadata.get("file_path", "unknown"),
            "file_name": node.metadata.get("file_name", "unknown"),
            "language": node.metadata.get("language", "unknown"),
            "score": node.score if hasattr(node, "score") else None,
            "text_snippet": node.text[:200] + "..." if len(node.text) > 200 else node.text,
        })
    
    return {
        "response": str(response),
        "sources": sources,
        "query": query,
        "source_count": len(sources),
    }


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    """CLI for testing queries"""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description="Query the codebase")
    parser.add_argument("query", help="Question to ask")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Top K results")
    
    args = parser.parse_args()
    
    print(f"🔍 Querying: {args.query}\n")
    
    engine = create_query_engine(similarity_top_k=args.top_k)
    result = asyncio.run(query_codebase(args.query, engine))
    
    print(f"📝 Response:\n{result['response']}\n")
    print(f"📚 Sources ({result['source_count']}):")
    for src in result["sources"]:
        print(f"  - {src['file_path']} ({src['language']}) - score: {src['score']:.3f}")


if __name__ == "__main__":
    main()
