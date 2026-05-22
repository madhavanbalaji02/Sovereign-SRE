"""
Lambda: Remediation Trigger
============================
Entry point for the EventBridge → Lambda → Step Functions flow.
Receives a CloudWatch Alarm event, starts the Step Functions execution,
and notifies the FastAPI backend for real-time WebSocket streaming.

Environment variables (set in setup.py):
  STATE_MACHINE_ARN  — Step Functions state machine ARN
  BACKEND_URL        — FastAPI backend URL (for WebSocket notification)
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone


def lambda_handler(event: dict, context) -> dict:
    alarm_name = event.get("detail", {}).get("alarmName", "unknown-alarm")
    new_state = event.get("detail", {}).get("state", {}).get("value", "")
    reason = event.get("detail", {}).get("state", {}).get("reason", "")
    event_time = event.get("time", datetime.now(timezone.utc).isoformat())

    if new_state != "ALARM":
        return {"statusCode": 200, "body": f"State is {new_state}, skipping"}

    incident_payload = {
        "trigger_source": "cloudwatch_alarm",
        "alarm_name": alarm_name,
        "alarm_reason": reason,
        "severity": "high",
        "log_group": "/sovereign-sre/incidents",
        "timestamp": event_time,
    }

    # -----------------------------------------------------------------------
    # 1. Start Step Functions execution (durable, tracks progress in DynamoDB)
    # -----------------------------------------------------------------------
    import boto3
    sf = boto3.client("stepfunctions")
    sm_arn = os.environ.get("STATE_MACHINE_ARN", "")

    execution_arn = ""
    if sm_arn:
        resp = sf.start_execution(
            stateMachineArn=sm_arn,
            input=json.dumps(incident_payload),
        )
        execution_arn = resp.get("executionArn", "")
        print(f"Started execution: {execution_arn}")
    else:
        print("WARNING: STATE_MACHINE_ARN not set — skipping Step Functions")

    # -----------------------------------------------------------------------
    # 2. Notify FastAPI backend for real-time WebSocket updates (best-effort)
    # -----------------------------------------------------------------------
    backend_url = os.environ.get("BACKEND_URL", "")
    if backend_url:
        try:
            req = urllib.request.Request(
                f"{backend_url}/api/pipeline/trigger",
                data=json.dumps(incident_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=25)
            print("Backend notified")
        except Exception as e:
            print(f"Backend notification failed (non-fatal): {e}")

    return {
        "statusCode": 200,
        "executionArn": execution_arn,
        "incident": incident_payload,
    }
