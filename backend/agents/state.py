"""
SRE Agent State
===============
Shared state schema for the LangGraph state machine.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class LogEntry(BaseModel):
    """Represents a log entry or error detected"""
    timestamp: str
    level: str  # ERROR, WARNING, INFO
    message: str
    source: Optional[str] = None
    stack_trace: Optional[str] = None


class RootCauseAnalysis(BaseModel):
    """Root cause analysis result"""
    summary: str
    affected_files: list[str]
    error_type: str
    confidence: float
    recommended_fix: str
    rag_sources: list[dict] = Field(default_factory=list)


class CodeFix(BaseModel):
    """Proposed code fix"""
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    diff: str


class ValidationResult(BaseModel):
    """Validation/test result"""
    passed: bool
    tests_run: int
    tests_passed: int
    tests_failed: int
    error_output: Optional[str] = None


class SREState(BaseModel):
    """
    Complete state for the SRE agent pipeline.
    
    This state is passed through all nodes in the LangGraph.
    """
    # Pipeline metadata
    run_id: str
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    current_node: str = "start"
    status: Literal["running", "waiting_approval", "completed", "failed"] = "running"
    
    # Log monitoring
    logs: list[LogEntry] = Field(default_factory=list)
    detected_issues: list[str] = Field(default_factory=list)
    
    # Root cause analysis
    root_cause: Optional[RootCauseAnalysis] = None
    crew_thoughts: list[dict] = Field(default_factory=list)
    
    # Code fixing
    proposed_fixes: list[CodeFix] = Field(default_factory=list)
    human_approved: bool = False
    approval_message: Optional[str] = None
    
    # Validation
    validation_result: Optional[ValidationResult] = None
    
    # GitHub PR
    pr_created: bool = False
    pr_url: Optional[str] = None
    
    # Messages for streaming
    messages: list[dict] = Field(default_factory=list)
    
    def add_message(self, role: str, content: str, node: Optional[str] = None):
        """Add a message to the stream"""
        self.messages.append({
            "role": role,
            "content": content,
            "node": node or self.current_node,
            "timestamp": datetime.utcnow().isoformat()
        })
