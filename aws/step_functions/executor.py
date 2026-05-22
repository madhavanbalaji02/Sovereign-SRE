"""
Step Functions Pipeline Executor
==================================
Start executions, poll status, and handle task token callbacks.
"""

import json
import uuid
from typing import Optional

import boto3

from aws.config import STATE_MACHINE_ARN, REGION


class PipelineExecutor:
    def __init__(self, state_machine_arn: str = STATE_MACHINE_ARN, region: str = REGION):
        self._sm_arn = state_machine_arn or STATE_MACHINE_ARN
        self._region = region
        self._client: Optional[object] = None

    def _sf(self):
        if self._client is None:
            self._client = boto3.client("stepfunctions", region_name=self._region)
        return self._client

    def start_execution(self, input_data: dict) -> str:
        """Start a new pipeline execution. Returns execution ARN."""
        if not self._sm_arn:
            raise RuntimeError("STATE_MACHINE_ARN not set")

        # Ensure incident_id is present
        if "incident_id" not in input_data:
            input_data = {**input_data, "incident_id": str(uuid.uuid4())}

        resp = self._sf().start_execution(
            stateMachineArn=self._sm_arn,
            input=json.dumps(input_data),
        )
        return resp["executionArn"]

    def get_status(self, execution_arn: str) -> dict:
        """Return status dict with keys: status, output, error."""
        resp = self._sf().describe_execution(executionArn=execution_arn)
        result = {
            "status": resp["status"],
            "startDate": resp.get("startDate", "").isoformat() if resp.get("startDate") else "",
            "stopDate": resp.get("stopDate", "").isoformat() if resp.get("stopDate") else "",
            "output": None,
            "error": None,
        }
        if resp.get("output"):
            try:
                result["output"] = json.loads(resp["output"])
            except Exception:
                result["output"] = resp["output"]
        if resp.get("error"):
            result["error"] = resp["error"]
        return result

    def send_task_success(self, task_token: str, output: dict) -> None:
        """Call when human approves — resumes Step Functions waitForTaskToken."""
        self._sf().send_task_success(
            taskToken=task_token,
            output=json.dumps(output),
        )

    def send_task_failure(self, task_token: str, error: str = "HumanRejected", cause: str = "") -> None:
        """Call when human rejects — causes Step Functions to take Catch path."""
        self._sf().send_task_failure(
            taskToken=task_token,
            error=error,
            cause=cause or "Fix rejected by human reviewer",
        )

    def list_executions(self, status_filter: Optional[str] = None) -> list[dict]:
        """List executions, optionally filtered by status (RUNNING, SUCCEEDED, FAILED, etc.)."""
        if not self._sm_arn:
            return []
        kwargs = {"stateMachineArn": self._sm_arn, "maxResults": 20}
        if status_filter:
            kwargs["statusFilter"] = status_filter

        resp = self._sf().list_executions(**kwargs)
        return [
            {
                "executionArn": e["executionArn"],
                "name": e["name"],
                "status": e["status"],
                "startDate": e["startDate"].isoformat(),
            }
            for e in resp.get("executions", [])
        ]
