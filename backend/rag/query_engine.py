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
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# =============================================================================
# CONFIGURATION
# =============================================================================

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://localhost:8000")
LLM_MODEL = os.environ.get("OLLAMA_LLM_MODEL", "llama3.3")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "bge-m3")
COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "sovereign_sre_codebase")


# =============================================================================
# QUERY ENGINE FACTORY
# =============================================================================

def create_query_engine(
    collection_name: str = COLLECTION_NAME,
    ollama_host: str = OLLAMA_HOST,
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
        ollama_host: Ollama API URL
        chroma_host: ChromaDB API URL
        llm_model: LLM model for response generation
        embed_model: Embedding model name
        similarity_top_k: Number of similar chunks to retrieve
        similarity_cutoff: Minimum similarity score
        
    Returns:
        Configured query engine
    """
    # Configure LLM
    llm = Ollama(
        model=llm_model,
        base_url=ollama_host,
        request_timeout=120.0,
    )
    Settings.llm = llm
    
    # Configure embeddings
    embed = OllamaEmbedding(
        model_name=embed_model,
        base_url=ollama_host,
    )
    Settings.embed_model = embed
    
    # Connect to ChromaDB
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
