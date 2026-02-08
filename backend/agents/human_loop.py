"""
Human-in-the-Loop Handler
=========================
Manages human approval breakpoints in the agent pipeline.
"""

import asyncio
from typing import Optional, Callable
from datetime import datetime
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Request for human approval"""
    run_id: str
    node: str
    action: str
    details: dict
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    approved: Optional[bool] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None
    message: Optional[str] = None


class HumanLoopManager:
    """
    Manages human-in-the-loop approvals for agent actions.
    
    This class provides a way to pause agent execution and wait for
    human approval before proceeding with potentially destructive actions.
    """
    
    def __init__(self):
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_events: dict[str, asyncio.Event] = {}
        self._callbacks: list[Callable] = []
    
    def register_callback(self, callback: Callable):
        """Register a callback to be called when approval is requested"""
        self._callbacks.append(callback)
    
    async def request_approval(
        self,
        run_id: str,
        node: str,
        action: str,
        details: dict,
    ) -> ApprovalRequest:
        """
        Request human approval for an action.
        
        This will pause execution until approval is received.
        
        Args:
            run_id: Pipeline run ID
            node: Current node requesting approval
            action: Description of the action needing approval
            details: Additional details about the action
            
        Returns:
            ApprovalRequest with approval decision
        """
        request = ApprovalRequest(
            run_id=run_id,
            node=node,
            action=action,
            details=details,
        )
        
        # Store pending approval
        self._pending_approvals[run_id] = request
        self._approval_events[run_id] = asyncio.Event()
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                await callback(request)
            except Exception:
                pass  # Don't let callback errors break the flow
        
        # Wait for approval
        await self._approval_events[run_id].wait()
        
        return self._pending_approvals[run_id]
    
    def approve(
        self,
        run_id: str,
        approved: bool,
        approved_by: str = "human",
        message: Optional[str] = None,
    ) -> bool:
        """
        Submit approval decision for a pending request.
        
        Args:
            run_id: Pipeline run ID
            approved: Whether the action is approved
            approved_by: Identifier of the approver
            message: Optional message from the approver
            
        Returns:
            True if approval was recorded, False if no pending request
        """
        if run_id not in self._pending_approvals:
            return False
        
        request = self._pending_approvals[run_id]
        request.approved = approved
        request.approved_at = datetime.utcnow().isoformat()
        request.approved_by = approved_by
        request.message = message
        
        # Signal waiting coroutine
        if run_id in self._approval_events:
            self._approval_events[run_id].set()
        
        return True
    
    def get_pending(self, run_id: Optional[str] = None) -> list[ApprovalRequest]:
        """Get pending approval requests"""
        if run_id:
            request = self._pending_approvals.get(run_id)
            return [request] if request and request.approved is None else []
        
        return [r for r in self._pending_approvals.values() if r.approved is None]
    
    def clear(self, run_id: str):
        """Clear a completed approval request"""
        self._pending_approvals.pop(run_id, None)
        self._approval_events.pop(run_id, None)


# Global manager instance
human_loop_manager = HumanLoopManager()
