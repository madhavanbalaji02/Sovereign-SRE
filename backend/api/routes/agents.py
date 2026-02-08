"""
Agents API Routes
=================
FastAPI endpoints for agent operations and WebSocket streaming.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional
import json
import asyncio

from backend.agents.graph import run_sre_pipeline
from backend.agents.state import SREState
from backend.agents.human_loop import human_loop_manager

router = APIRouter(prefix="/agents", tags=["Agents"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class RunPipelineRequest(BaseModel):
    """Request to run the SRE pipeline"""
    logs: list[dict] = Field(..., description="Log entries to analyze")
    run_id: Optional[str] = Field(None, description="Optional run ID")
    auto_approve: bool = Field(False, description="Auto-approve fixes (skip human loop)")


class RunPipelineResponse(BaseModel):
    """Response from pipeline run"""
    run_id: str
    status: str
    current_node: str
    detected_issues: list[str]
    waiting_approval: bool
    messages: list[dict]


class ApprovalRequest(BaseModel):
    """Request to approve a pending action"""
    run_id: str
    approved: bool
    message: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Response from approval"""
    success: bool
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/run", response_model=RunPipelineResponse)
async def run_pipeline(request: RunPipelineRequest):
    """
    Run the SRE agent pipeline.
    
    The pipeline will:
    1. Analyze logs for issues
    2. Perform root cause analysis
    3. Generate code fixes
    4. Wait for human approval (unless auto_approve=true)
    5. Validate fixes with tests
    """
    try:
        result = await run_sre_pipeline(
            logs=request.logs,
            run_id=request.run_id,
            human_approved=request.auto_approve,
        )
        
        return RunPipelineResponse(
            run_id=result.run_id,
            status=result.status,
            current_node=result.current_node,
            detected_issues=result.detected_issues,
            waiting_approval=result.status == "waiting_approval",
            messages=result.messages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@router.post("/approve", response_model=ApprovalResponse)
async def approve_action(request: ApprovalRequest):
    """
    Approve or reject a pending action.
    
    Use this to respond to human-in-the-loop breakpoints.
    """
    success = human_loop_manager.approve(
        run_id=request.run_id,
        approved=request.approved,
        message=request.message,
    )
    
    if success:
        return ApprovalResponse(
            success=True,
            message=f"Action {'approved' if request.approved else 'rejected'}"
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No pending approval for run_id: {request.run_id}"
        )


@router.get("/pending")
async def get_pending_approvals():
    """Get all pending approval requests"""
    pending = human_loop_manager.get_pending()
    return {
        "pending": [p.model_dump() for p in pending],
        "count": len(pending),
    }


# =============================================================================
# WEBSOCKET FOR STREAMING
# =============================================================================

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, run_id: str):
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
    
    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for streaming agent events.
    
    Connect to receive real-time updates about:
    - Agent thoughts and decisions
    - State transitions
    - Approval requests
    - Validation results
    """
    await manager.connect(websocket, run_id)
    
    try:
        while True:
            # Receive messages from client (e.g., approvals)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "approve":
                human_loop_manager.approve(
                    run_id=run_id,
                    approved=message.get("approved", False),
                    message=message.get("message"),
                )
                await manager.broadcast(run_id, {
                    "type": "approval_received",
                    "approved": message.get("approved"),
                })
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)
