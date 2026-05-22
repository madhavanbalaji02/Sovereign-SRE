"""
AWS Integration Routes
=======================
New API endpoints for Step Functions pipeline triggering,
incident history (DynamoDB), artifact retrieval (S3),
human approval webhook (SNS/Step Functions), and metrics summary.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["AWS"])


# =============================================================================
# Models
# =============================================================================

class TriggerRequest(BaseModel):
    trigger_source: str = Field(default="manual")
    alarm_name: str = Field(default="")
    alarm_reason: str = Field(default="")
    severity: str = Field(default="high")
    log_group: str = Field(default="/sovereign-sre/incidents")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    logs: list[dict] = Field(default_factory=list)


# =============================================================================
# POST /api/pipeline/trigger
# =============================================================================

@router.post("/api/pipeline/trigger")
async def trigger_pipeline(request: TriggerRequest):
    """
    Start the healing pipeline via Step Functions (durable) + LangGraph (real-time).

    Called by:
    - Lambda remediation trigger (CloudWatch alarm path)
    - Manual API calls
    """
    import asyncio

    incident_id = str(uuid.uuid4())

    # Build log entries from the trigger context
    logs = request.logs or [{
        "level": "ERROR",
        "message": request.alarm_reason or f"Alarm triggered: {request.alarm_name}",
        "timestamp": request.timestamp,
        "source": request.alarm_name or "cloudwatch",
    }]

    # -----------------------------------------------------------------------
    # 1. Start Step Functions execution (durable path)
    # -----------------------------------------------------------------------
    execution_arn = ""
    try:
        from aws.step_functions.executor import PipelineExecutor
        executor = PipelineExecutor()
        execution_arn = executor.start_execution({
            "incident_id": incident_id,
            "trigger_source": request.trigger_source,
            "alarm_name": request.alarm_name,
            "severity": request.severity,
            "anomaly_detected": True,
            "logs": logs,
        })
    except Exception as e:
        # Step Functions may not be set up — continue with LangGraph only
        print(f"[aws_routes] Step Functions skipped: {e}")

    # -----------------------------------------------------------------------
    # 2. Start LangGraph pipeline in background (real-time WebSocket streaming)
    # -----------------------------------------------------------------------
    async def _run_langgraph():
        try:
            from backend.agents.graph import run_sre_pipeline
            await run_sre_pipeline(
                logs=logs,
                run_id=incident_id,
                trigger_source=request.trigger_source,
                alarm_name=request.alarm_name,
            )
        except Exception as e:
            print(f"[aws_routes] LangGraph pipeline error: {e}")

    asyncio.create_task(_run_langgraph())

    return {
        "incident_id": incident_id,
        "execution_arn": execution_arn,
        "status": "started",
        "message": "Pipeline started (Step Functions + LangGraph)",
    }


# =============================================================================
# GET /api/incidents
# =============================================================================

@router.get("/api/incidents")
async def list_incidents(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
):
    """List incidents from DynamoDB (most recent first)."""
    try:
        from aws.dynamodb.incident_store import IncidentStore
        store = IncidentStore()
        incidents = store.list_incidents(limit=limit, status=status)
        return {"incidents": incidents, "count": len(incidents)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DynamoDB unavailable: {e}")


# =============================================================================
# GET /api/incidents/{incident_id}
# =============================================================================

@router.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get full incident details + presigned S3 artifact URLs."""
    try:
        from aws.dynamodb.incident_store import IncidentStore
        store = IncidentStore()
        incident = store.get_incident(incident_id)

        if not incident:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

        # Attach presigned URLs for S3 artifacts
        try:
            from aws.s3.artifact_store import ArtifactStore
            artifacts = ArtifactStore()
            artifact_keys = artifacts.list_incident_artifacts(incident_id)
            incident["artifacts"] = {
                key.split("/")[-1]: artifacts.get_presigned_url(key)
                for key in artifact_keys
            }
        except Exception:
            incident["artifacts"] = {}

        return incident
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# =============================================================================
# POST /api/approvals/{incident_id}
# =============================================================================

@router.post("/api/approvals/{incident_id}", response_class=HTMLResponse)
async def handle_approval(
    incident_id: str,
    action: str = Query(..., regex="^(approve|reject)$"),
    token: str = Query(...),
):
    """
    Human approval webhook — called when user clicks approve/reject email link.
    Resumes the Step Functions waitForTaskToken state.
    Updates DynamoDB approval_status.
    Returns a simple HTML confirmation page.
    """
    approved = action == "approve"

    # Resume Step Functions
    try:
        from aws.step_functions.executor import PipelineExecutor
        executor = PipelineExecutor()
        if approved:
            executor.send_task_success(
                task_token=token,
                output={"approved": True, "incident_id": incident_id},
            )
        else:
            executor.send_task_failure(
                task_token=token,
                error="HumanRejected",
                cause=f"Fix rejected by human reviewer for incident {incident_id}",
            )
    except Exception as e:
        print(f"[aws_routes] Step Functions task callback failed: {e}")

    # Update DynamoDB
    try:
        from aws.dynamodb.incident_store import IncidentStore
        store = IncidentStore()
        incident = store.get_incident(incident_id)
        if incident:
            store.update_incident(
                incident_id=incident_id,
                timestamp=incident["timestamp"],
                approval_status="approved" if approved else "rejected",
            )
    except Exception:
        pass

    # Also update the in-process human loop manager (for LangGraph streaming path)
    try:
        from backend.agents.human_loop import human_loop_manager
        human_loop_manager.approve(
            run_id=incident_id,
            approved=approved,
            approved_by="email_link",
        )
    except Exception:
        pass

    action_word = "approved" if approved else "rejected"
    color = "#00ff88" if approved else "#ff4444"
    emoji = "✅" if approved else "❌"

    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Sovereign SRE — Approval</title>
<style>
  body {{ background: #0a0e1a; color: #c9d1d9; font-family: 'Courier New', monospace;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
  .card {{ background: #111827; border: 1px solid {color}; border-radius: 8px;
           padding: 3rem; text-align: center; max-width: 480px; }}
  h1 {{ color: {color}; font-size: 1.8rem; margin-bottom: 1rem; }}
  p {{ color: #8b949e; line-height: 1.6; }}
  code {{ color: #00ffff; }}
</style>
</head>
<body>
  <div class="card">
    <h1>{emoji} Fix {action_word}</h1>
    <p>Incident <code>{incident_id}</code> has been <strong>{action_word}</strong>.</p>
    {"<p>Sovereign-SRE will now apply the patch and run validation.</p>" if approved else
     "<p>The incident has been marked as unresolved. No changes will be applied.</p>"}
  </div>
</body>
</html>""")


# =============================================================================
# GET /api/metrics/summary
# =============================================================================

@router.get("/api/metrics/summary")
async def metrics_summary():
    """Return last 7 days: total incidents, fix rate, avg resolution time, Bedrock cost."""
    try:
        from aws.dynamodb.incident_store import IncidentStore
        store = IncidentStore()
        all_incidents = store.list_incidents(limit=200)

        total = len(all_incidents)
        resolved = sum(1 for i in all_incidents if i.get("status") == "resolved")
        failed = sum(1 for i in all_incidents if i.get("status") == "failed")

        resolution_times = [
            int(i.get("resolution_time_ms", 0))
            for i in all_incidents
            if int(i.get("resolution_time_ms", 0)) > 0
        ]
        avg_resolution_ms = (
            sum(resolution_times) / len(resolution_times) if resolution_times else 0
        )

        costs = [
            float(i.get("cost_usd", 0))
            for i in all_incidents
            if float(i.get("cost_usd", 0)) > 0
        ]
        total_bedrock_cost = sum(costs)

        return {
            "period_days": 7,
            "total_incidents": total,
            "resolved": resolved,
            "failed": failed,
            "fix_rate_pct": round((resolved / total * 100) if total else 0, 1),
            "avg_resolution_ms": round(avg_resolution_ms),
            "total_bedrock_cost_usd": round(total_bedrock_cost, 4),
        }
    except Exception as e:
        return {"error": str(e), "total_incidents": 0}
