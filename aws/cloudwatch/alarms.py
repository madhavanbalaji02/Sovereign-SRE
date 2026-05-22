"""
CloudWatch Alarms
=================
Create and manage alarms that auto-trigger the healing pipeline.

# COST SAFE: CW Alarms <10 = $0
"""

from typing import Optional

import boto3

from aws.config import CW_NAMESPACE, REGION


class AlarmManager:
    def __init__(self, region: str = REGION, sns_topic_arn: str = ""):
        self._region = region
        self._sns_topic_arn = sns_topic_arn
        self._client: Optional[object] = None

    def _cw(self):
        if self._client is None:
            self._client = boto3.client("cloudwatch", region_name=self._region)
        return self._client

    def _actions(self) -> list[str]:
        return [self._sns_topic_arn] if self._sns_topic_arn else []

    def create_standard_alarms(self) -> None:
        """Create the standard set of Sovereign-SRE alarms."""
        self.create_alarm(
            name="sovereign-sre-ErrorRate",
            description="More than 5 pipeline errors in 2 minutes",
            metric="ErrorRate",
            threshold=5,
            period=120,
            evaluation_periods=1,
            comparison="GreaterThanOrEqualToThreshold",
        )
        self.create_alarm(
            name="sovereign-sre-PipelineFailureRate",
            description="Pipeline failure rate > 20%",
            metric="PipelineFailure",
            threshold=2,
            period=300,
            evaluation_periods=1,
            comparison="GreaterThanOrEqualToThreshold",
        )
        self.create_alarm(
            name="sovereign-sre-ApprovalWaitTime",
            description="Approval waiting longer than 30 minutes",
            metric="ApprovalWaitSeconds",
            threshold=1800,
            period=60,
            evaluation_periods=1,
            comparison="GreaterThanOrEqualToThreshold",
        )

    def create_alarm(
        self,
        name: str,
        description: str,
        metric: str,
        threshold: float,
        period: int = 60,
        evaluation_periods: int = 1,
        comparison: str = "GreaterThanOrEqualToThreshold",
        namespace: str = CW_NAMESPACE,
        statistic: str = "Sum",
    ) -> None:
        self._cw().put_metric_alarm(
            AlarmName=name,
            AlarmDescription=description,
            Namespace=namespace,
            MetricName=metric,
            Period=period,
            EvaluationPeriods=evaluation_periods,
            Threshold=threshold,
            ComparisonOperator=comparison,
            Statistic=statistic,
            AlarmActions=self._actions(),
            OKActions=self._actions(),
            TreatMissingData="notBreaching",
        )

    def delete_alarm(self, name: str) -> None:
        self._cw().delete_alarms(AlarmNames=[name])

    def list_alarms(self, prefix: str = "sovereign-sre") -> list[dict]:
        resp = self._cw().describe_alarms(AlarmNamePrefix=prefix)
        return resp.get("MetricAlarms", [])
