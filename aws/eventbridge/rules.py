"""
EventBridge Rules
==================
Route CloudWatch Alarm state changes → Lambda → Step Functions pipeline.
"""

import json
from typing import Optional

import boto3

from aws.config import EVENTBRIDGE_RULE_NAME, REGION


class EventBridgeManager:
    ALARM_EVENT_PATTERN = {
        "source": ["aws.cloudwatch"],
        "detail-type": ["CloudWatch Alarm State Change"],
        "detail": {
            "state": {"value": ["ALARM"]},
            "alarmName": [{"prefix": "sovereign-sre"}],
        },
    }

    def __init__(self, region: str = REGION):
        self._region = region
        self._client: Optional[object] = None

    def _eb(self):
        if self._client is None:
            self._client = boto3.client("events", region_name=self._region)
        return self._client

    def create_alarm_trigger_rule(self) -> str:
        """Create/update the alarm → Lambda EventBridge rule. Returns Rule ARN."""
        resp = self._eb().put_rule(
            Name=EVENTBRIDGE_RULE_NAME,
            EventPattern=json.dumps(self.ALARM_EVENT_PATTERN),
            State="ENABLED",
            Description="Route sovereign-sre CloudWatch alarms to remediation Lambda",
        )
        return resp["RuleArn"]

    def add_lambda_target(self, lambda_arn: str) -> None:
        """Add Lambda as the target for the alarm trigger rule."""
        self._eb().put_targets(
            Rule=EVENTBRIDGE_RULE_NAME,
            Targets=[
                {
                    "Id": "sovereign-sre-lambda-target",
                    "Arn": lambda_arn,
                }
            ],
        )

    def grant_lambda_invoke(self, lambda_client, lambda_name: str, rule_arn: str) -> None:
        """Grant EventBridge permission to invoke the Lambda function."""
        try:
            lambda_client.add_permission(
                FunctionName=lambda_name,
                StatementId="sovereign-sre-eventbridge-invoke",
                Action="lambda:InvokeFunction",
                Principal="events.amazonaws.com",
                SourceArn=rule_arn,
            )
        except lambda_client.exceptions.ResourceConflictException:
            pass  # Permission already exists

    def delete_rule(self) -> None:
        try:
            self._eb().remove_targets(
                Rule=EVENTBRIDGE_RULE_NAME,
                Ids=["sovereign-sre-lambda-target"],
            )
        except Exception:
            pass
        try:
            self._eb().delete_rule(Name=EVENTBRIDGE_RULE_NAME)
        except Exception:
            pass

    def get_rule_arn(self) -> Optional[str]:
        try:
            resp = self._eb().describe_rule(Name=EVENTBRIDGE_RULE_NAME)
            return resp.get("Arn")
        except Exception:
            return None
