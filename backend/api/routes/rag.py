"""
RAG API Routes
==============
FastAPI endpoints for RAG operations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.rag.codebase_observer import CodebaseObserver
from backend.rag.query_engine import query_codebase, create_query_engine

router = APIRouter(prefix="/rag", tags=["RAG"])

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class QueryRequest(BaseModel):
    """Request model for codebase query"""
    query: str = Field(..., description="Natural language question about the codebase")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of similar chunks to retrieve")


class QueryResponse(BaseModel):
    """Response model for codebase query"""
    response: str
    sources: list[dict]
    query: str
    source_count: int


class IndexRequest(BaseModel):
    """Request model for indexing"""
    force_reindex: bool = Field(default=False, description="Clear and rebuild index")


class IndexResponse(BaseModel):
    """Response model for indexing"""
    status: str
    chunks_indexed: int
    message: str


class StatsResponse(BaseModel):
    """Response model for index stats"""
    collection_name: str
    chunk_count: int
    workspace_path: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/query", response_model=QueryResponse)
async def rag_query(request: QueryRequest):
    """
    Query the indexed codebase.
    
    Ask natural language questions like:
    - "How is error handling implemented in the FastAPI router?"
    - "What is the purpose of the CodebaseObserver class?"
    - "Show me how authentication is configured"
    """
    try:
        engine = create_query_engine(similarity_top_k=request.top_k)
        result = await query_codebase(request.query, engine)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/index", response_model=IndexResponse)
async def index_codebase(request: IndexRequest):
    """
    Index or reindex the codebase.
    
    Set force_reindex=true to clear existing index and rebuild.
    """
    try:
        observer = CodebaseObserver()
        index = observer.index_codebase(force_reindex=request.force_reindex)
        stats = observer.get_stats()
        
        return IndexResponse(
            status="success",
            chunks_indexed=stats.get("chunk_count", 0),
            message=f"Indexed {stats.get('chunk_count', 0)} chunks from {observer.workspace_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get current index statistics"""
    try:
        observer = CodebaseObserver()
        stats = observer.get_stats()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
