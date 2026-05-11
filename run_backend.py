#!/usr/bin/env python3
"""
Standalone Backend Server
=========================
Simplified version that runs without Docker for local development.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json

app = FastAPI(
    title="Sovereign-SRE Backend",
    description="Backend API for autonomous SRE operations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# MODELS
# =============================================================================

class RunPipelineRequest(BaseModel):
    logs: list[dict] = Field(..., description="Log entries to analyze")
    run_id: Optional[str] = Field(None, description="Optional run ID")
    auto_approve: bool = Field(False, description="Auto-approve fixes")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Question about the codebase")
    top_k: int = Field(default=5)


# =============================================================================
# DEMO STATE
# =============================================================================

demo_state = {
    "status": "idle",
    "current_node": "idle",
    "detected_issues": [],
    "thoughts": [],
    "messages": []
}


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/")
async def root():
    return {
        "name": "Sovereign-SRE Backend (Standalone)",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.post("/api/agents/run")
async def run_pipeline(request: RunPipelineRequest):
    """Simulate running the SRE pipeline"""
    import uuid
    import asyncio
    
    run_id = request.run_id or str(uuid.uuid4())
    
    # Simulate pipeline execution
    demo_state["status"] = "running"
    demo_state["current_node"] = "log_monitor"
    demo_state["detected_issues"] = []
    demo_state["thoughts"] = []
    
    # Analyze logs
    for log in request.logs:
        if log.get("level", "").upper() in ["ERROR", "CRITICAL"]:
            demo_state["detected_issues"].append(log.get("message", "Unknown error"))
    
    demo_state["thoughts"].append({
        "agent": "LogMonitor",
        "thought": f"Detected {len(demo_state['detected_issues'])} issues",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    if demo_state["detected_issues"]:
        demo_state["current_node"] = "root_cause_analyst"
        demo_state["thoughts"].append({
            "agent": "Senior SRE",
            "thought": "Analyzing root cause of detected errors...",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        demo_state["current_node"] = "code_fixer"
        demo_state["thoughts"].append({
            "agent": "CodeFixer",
            "thought": "Generating fix for identified issue",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        if request.auto_approve:
            demo_state["current_node"] = "validator"
            demo_state["thoughts"].append({
                "agent": "Validator",
                "thought": "Running tests to validate fix",
                "timestamp": datetime.utcnow().isoformat()
            })
            demo_state["status"] = "completed"
        else:
            demo_state["status"] = "waiting_approval"
    else:
        demo_state["status"] = "completed"
    
    return {
        "run_id": run_id,
        "status": demo_state["status"],
        "current_node": demo_state["current_node"],
        "detected_issues": demo_state["detected_issues"],
        "waiting_approval": demo_state["status"] == "waiting_approval",
        "messages": demo_state["thoughts"]
    }


@app.post("/api/agents/approve")
async def approve_action(run_id: str, approved: bool):
    """Approve or reject a pending fix"""
    if approved:
        demo_state["status"] = "completed"
        demo_state["current_node"] = "validator"
        return {"success": True, "message": "Fix approved and applied"}
    else:
        demo_state["status"] = "failed"
        return {"success": True, "message": "Fix rejected"}


@app.get("/api/agents/pending")
async def get_pending():
    """Get pending approvals"""
    if demo_state["status"] == "waiting_approval":
        return {"pending": [demo_state], "count": 1}
    return {"pending": [], "count": 0}


@app.post("/api/rag/query")
async def query_codebase(request: QueryRequest):
    """Simulate RAG query"""
    return {
        "response": f"Based on the codebase analysis, here's the answer to: '{request.query}'...\n\n(RAG requires ChromaDB + indexed codebase for real responses)",
        "sources": [
            {"file_path": "backend/api/main.py", "language": "python", "score": 0.85}
        ],
        "query": request.query,
        "source_count": 1
    }


@app.get("/api/rag/stats")
async def rag_stats():
    """Get RAG stats"""
    return {
        "collection_name": "sovereign_sre_codebase",
        "chunk_count": 0,
        "workspace_path": "/workspace"
    }


# =============================================================================
# WEBSOCKET
# =============================================================================

@app.websocket("/api/agents/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Sovereign-SRE Backend (Standalone Mode)")
    print("📚 Docs: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)
