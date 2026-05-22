"""
CloudWatch Custom Metrics
=========================
Namespace: SovereignSRE

# COST SAFE: CW Alarms <10 = $0, Logs <5GB = $0
"""

import os
from datetime import datetime, timezone
from typing import Optional

import boto3

from aws.config import CW_NAMESPACE, REGION


class SREMetrics:
    def __init__(self, namespace: str = CW_NAMESPACE, region: str = REGION):
        self._namespace = namespace
        self._region = region
        self._client: Optional[object] = None

    def _cw(self):
        if self._client is None:
            self._client = boto3.client("cloudwatch", region_name=self._region)
        return self._client

    def push(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[list[dict]] = None,
    ) -> None:
        metric = {
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
        }
        if dimensions:
            metric["Dimensions"] = dimensions

        try:
            self._cw().put_metric_data(
                Namespace=self._namespace,
                MetricData=[metric],
            )
        except Exception as e:
            # Non-fatal: metrics failure must never break the pipeline
            print(f"[SREMetrics] push failed ({metric_name}): {e}")

    # ------------------------------------------------------------------
    # Pre-built pushers
    # ------------------------------------------------------------------

    def record_pipeline_start(self, incident_id: str) -> None:
        self.push("PipelineStart", 1, dimensions=[
            {"Name": "IncidentId", "Value": incident_id},
        ])

    def record_pipeline_complete(
        self, incident_id: str, duration_ms: float, success: bool
    ) -> None:
        self.push("PipelineComplete", 1, dimensions=[
            {"Name": "IncidentId", "Value": incident_id},
            {"Name": "Success", "Value": str(success)},
        ])
        self.push("PipelineDurationMs", duration_ms, unit="Milliseconds")
        if not success:
            self.push("PipelineFailure", 1)

    def record_fix_applied(self, incident_id: str, confidence_score: float) -> None:
        self.push("FixApplied", 1, dimensions=[
            {"Name": "IncidentId", "Value": incident_id},
        ])
        self.push("FixConfidence", confidence_score * 100, unit="Percent")

    def record_approval_wait(self, incident_id: str, wait_seconds: float) -> None:
        self.push("ApprovalWaitSeconds", wait_seconds, unit="Seconds", dimensions=[
            {"Name": "IncidentId", "Value": incident_id},
        ])

    def record_bedrock_tokens(
        self, input_tokens: int, output_tokens: int, model: str
    ) -> None:
        dims = [{"Name": "Model", "Value": model}]
        self.push("BedrockInputTokens", input_tokens, dimensions=dims)
        self.push("BedrockOutputTokens", output_tokens, dimensions=dims)
        # Haiku pricing: $0.00025/1K input, $0.00125/1K output
        cost = (input_tokens / 1000 * 0.00025) + (output_tokens / 1000 * 0.00125)
        self.push("BedrockCostUSD", cost, unit="None")

    def record_error(self, error_type: str) -> None:
        self.push("ErrorRate", 1, dimensions=[
            {"Name": "ErrorType", "Value": error_type},
        ])
