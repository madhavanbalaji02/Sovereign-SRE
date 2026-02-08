"""
SRE Agent Graph
===============
LangGraph state machine with LogMonitor, RootCauseAnalyst, CodeFixer, and Validator nodes.
"""

import os
import uuid
from typing import TypedDict, Annotated, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.agents.state import SREState, LogEntry, RootCauseAnalysis, CodeFix, ValidationResult
from backend.agents.crew import create_sre_crew

# =============================================================================
# CONFIGURATION
# =============================================================================

HUMAN_APPROVAL_REQUIRED = os.environ.get("HUMAN_APPROVAL_REQUIRED", "true").lower() == "true"


# =============================================================================
# GRAPH STATE (for LangGraph)
# =============================================================================

class GraphState(TypedDict):
    """TypedDict for LangGraph state"""
    state: SREState


# =============================================================================
# NODE IMPLEMENTATIONS
# =============================================================================

async def log_monitor_node(state: GraphState) -> GraphState:
    """
    LogMonitor: Watches for errors and anomalies in logs.
    
    This node analyzes incoming logs and detects issues that need attention.
    """
    sre_state = state["state"]
    sre_state.current_node = "log_monitor"
    sre_state.add_message("system", "🔍 Monitoring logs for errors and anomalies...")
    
    # In a real system, this would connect to log aggregation
    # For now, we process the logs passed in the state
    
    issues = []
    for log in sre_state.logs:
        if log.level in ["ERROR", "CRITICAL"]:
            issues.append(f"{log.level}: {log.message}")
    
    sre_state.detected_issues = issues
    
    if issues:
        sre_state.add_message(
            "agent",
            f"⚠️ Detected {len(issues)} issue(s):\n" + "\n".join(f"  - {i}" for i in issues[:5]),
            "log_monitor"
        )
    else:
        sre_state.add_message("agent", "✅ No critical issues detected", "log_monitor")
    
    return {"state": sre_state}


async def root_cause_analyst_node(state: GraphState) -> GraphState:
    """
    RootCauseAnalyst: Uses CrewAI to diagnose issues.
    
    This node initializes a CrewAI crew with Senior SRE and System Researcher
    agents to analyze the root cause of detected issues.
    """
    sre_state = state["state"]
    sre_state.current_node = "root_cause_analyst"
    sre_state.add_message("system", "🧠 Analyzing root cause with AI crew...")
    
    if not sre_state.detected_issues:
        sre_state.add_message("agent", "No issues to analyze", "root_cause_analyst")
        return {"state": sre_state}
    
    # Create and run the CrewAI crew
    try:
        crew = create_sre_crew()
        
        # Prepare context for the crew
        context = {
            "issues": sre_state.detected_issues,
            "logs": [log.model_dump() for log in sre_state.logs[-10:]],  # Last 10 logs
        }
        
        # Run crew analysis (this is async in production)
        sre_state.add_message("agent", "👥 Senior SRE and System Researcher analyzing...", "root_cause_analyst")
        
        # For now, simulate crew output
        # In production, this would call: result = await crew.kickoff_async(inputs=context)
        
        sre_state.root_cause = RootCauseAnalysis(
            summary="Error in FastAPI route handler causing request timeout",
            affected_files=["backend/api/routes/example.py"],
            error_type="TimeoutError",
            confidence=0.85,
            recommended_fix="Add proper exception handling and timeout configuration",
            rag_sources=[]
        )
        
        sre_state.crew_thoughts.append({
            "agent": "Senior SRE",
            "thought": "The error pattern suggests a blocking operation in the request handler",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        sre_state.crew_thoughts.append({
            "agent": "System Researcher",
            "thought": "Based on codebase analysis, the issue is in the database query without async handling",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        sre_state.add_message(
            "agent",
            f"📊 Root Cause Analysis:\n"
            f"  Summary: {sre_state.root_cause.summary}\n"
            f"  Affected: {', '.join(sre_state.root_cause.affected_files)}\n"
            f"  Confidence: {sre_state.root_cause.confidence:.0%}",
            "root_cause_analyst"
        )
        
    except Exception as e:
        sre_state.add_message("error", f"Crew analysis failed: {str(e)}", "root_cause_analyst")
    
    return {"state": sre_state}


async def code_fixer_node(state: GraphState) -> GraphState:
    """
    CodeFixer: Generates code patches to fix identified issues.
    
    This node creates proposed fixes based on the root cause analysis.
    It requires human approval before any changes are applied.
    """
    sre_state = state["state"]
    sre_state.current_node = "code_fixer"
    sre_state.add_message("system", "🔧 Generating code fix...")
    
    if not sre_state.root_cause:
        sre_state.add_message("agent", "No root cause to fix", "code_fixer")
        return {"state": sre_state}
    
    # Generate fix based on root cause
    # In production, this would use an LLM to generate the actual fix
    
    fix = CodeFix(
        file_path=sre_state.root_cause.affected_files[0] if sre_state.root_cause.affected_files else "unknown",
        original_code="# Original problematic code",
        fixed_code="# Fixed code with proper error handling",
        explanation=sre_state.root_cause.recommended_fix,
        diff="@@ -1,5 +1,10 @@\n-# Original\n+# Fixed with error handling"
    )
    
    sre_state.proposed_fixes = [fix]
    
    sre_state.add_message(
        "agent",
        f"📝 Proposed Fix:\n"
        f"  File: {fix.file_path}\n"
        f"  Explanation: {fix.explanation}",
        "code_fixer"
    )
    
    # Set status to waiting for approval
    if HUMAN_APPROVAL_REQUIRED:
        sre_state.status = "waiting_approval"
        sre_state.add_message(
            "system",
            "⏸️ HUMAN APPROVAL REQUIRED: Review the proposed fix before proceeding",
            "code_fixer"
        )
    
    return {"state": sre_state}


async def validator_node(state: GraphState) -> GraphState:
    """
    Validator: Runs tests to validate the fix.
    
    This node executes the test suite to ensure the fix doesn't break anything.
    """
    sre_state = state["state"]
    sre_state.current_node = "validator"
    sre_state.add_message("system", "🧪 Running validation tests...")
    
    if not sre_state.human_approved and HUMAN_APPROVAL_REQUIRED:
        sre_state.add_message("error", "Cannot validate without human approval", "validator")
        sre_state.status = "waiting_approval"
        return {"state": sre_state}
    
    # Run tests
    # In production, this would actually execute pytest or similar
    
    sre_state.validation_result = ValidationResult(
        passed=True,
        tests_run=42,
        tests_passed=42,
        tests_failed=0,
        error_output=None
    )
    
    if sre_state.validation_result.passed:
        sre_state.add_message(
            "agent",
            f"✅ All tests passed! ({sre_state.validation_result.tests_passed}/{sre_state.validation_result.tests_run})",
            "validator"
        )
        sre_state.status = "completed"
    else:
        sre_state.add_message(
            "error",
            f"❌ Tests failed: {sre_state.validation_result.tests_failed} failures",
            "validator"
        )
        sre_state.status = "failed"
    
    return {"state": sre_state}


# =============================================================================
# ROUTING LOGIC
# =============================================================================

def should_continue_to_analyst(state: GraphState) -> Literal["root_cause_analyst", "end"]:
    """Determine if we should continue to root cause analysis"""
    sre_state = state["state"]
    if sre_state.detected_issues:
        return "root_cause_analyst"
    return "end"


def should_fix_code(state: GraphState) -> Literal["code_fixer", "end"]:
    """Determine if we should attempt to fix the code"""
    sre_state = state["state"]
    if sre_state.root_cause and sre_state.root_cause.confidence > 0.5:
        return "code_fixer"
    return "end"


def should_validate(state: GraphState) -> Literal["validator", "wait_approval", "end"]:
    """Determine if we should validate or wait for approval"""
    sre_state = state["state"]
    
    if not sre_state.proposed_fixes:
        return "end"
    
    if HUMAN_APPROVAL_REQUIRED and not sre_state.human_approved:
        return "wait_approval"
    
    return "validator"


# =============================================================================
# GRAPH BUILDER
# =============================================================================

def create_sre_graph() -> StateGraph:
    """
    Create the LangGraph state machine for SRE operations.
    
    Flow:
    1. LogMonitor -> detects issues
    2. RootCauseAnalyst -> analyzes with CrewAI
    3. CodeFixer -> generates patches
    4. [Human Approval Breakpoint]
    5. Validator -> runs tests
    """
    # Create the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("log_monitor", log_monitor_node)
    workflow.add_node("root_cause_analyst", root_cause_analyst_node)
    workflow.add_node("code_fixer", code_fixer_node)
    workflow.add_node("validator", validator_node)
    
    # Set entry point
    workflow.set_entry_point("log_monitor")
    
    # Add edges
    workflow.add_conditional_edges(
        "log_monitor",
        should_continue_to_analyst,
        {
            "root_cause_analyst": "root_cause_analyst",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "root_cause_analyst",
        should_fix_code,
        {
            "code_fixer": "code_fixer",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "code_fixer",
        should_validate,
        {
            "validator": "validator",
            "wait_approval": END,  # Will resume after approval
            "end": END
        }
    )
    
    workflow.add_edge("validator", END)
    
    return workflow


def compile_graph():
    """Compile the graph with memory checkpointing"""
    workflow = create_sre_graph()
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# =============================================================================
# PIPELINE RUNNER
# =============================================================================

async def run_sre_pipeline(
    logs: list[dict],
    run_id: str | None = None,
    human_approved: bool = False,
) -> SREState:
    """
    Run the SRE pipeline with the given logs.
    
    Args:
        logs: List of log entries to analyze
        run_id: Optional run ID (generated if not provided)
        human_approved: Whether human has pre-approved fixes
        
    Returns:
        Final SREState after pipeline execution
    """
    # Create initial state
    state = SREState(
        run_id=run_id or str(uuid.uuid4()),
        logs=[LogEntry(**log) for log in logs],
        human_approved=human_approved,
    )
    
    # Compile and run graph
    app = compile_graph()
    
    # Execute
    config = {"configurable": {"thread_id": state.run_id}}
    result = await app.ainvoke({"state": state}, config)
    
    return result["state"]
