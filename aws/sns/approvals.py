"""
SNS Email Approval Gate
========================
Sends approval request emails via SNS.
The task_token is the Step Functions waitForTaskToken value —
approving calls send_task_success(), rejecting calls send_task_failure().

# COST SAFE: SNS <1M emails/month = $0
"""

import os
from typing import Optional

import boto3

from aws.config import SNS_TOPIC_ARN, BACKEND_URL, REGION


class SNSApprovalManager:
    def __init__(
        self,
        topic_arn: str = SNS_TOPIC_ARN,
        backend_url: str = BACKEND_URL,
        region: str = REGION,
    ):
        self._topic_arn = topic_arn or os.environ.get("SNS_TOPIC_ARN", "")
        self._backend_url = backend_url
        self._region = region
        self._client: Optional[object] = None

    def _sns(self):
        if self._client is None:
            self._client = boto3.client("sns", region_name=self._region)
        return self._client

    def is_configured(self) -> bool:
        return bool(self._topic_arn)

    def request_approval(
        self,
        incident_id: str,
        summary: str,
        diff_preview: str,
        task_token: str,
    ) -> None:
        """Publish an approval request email to the SNS topic."""
        if not self.is_configured():
            raise RuntimeError("SNS_TOPIC_ARN not set — cannot send email approval")

        approve_url = (
            f"{self._backend_url}/api/approvals/{incident_id}"
            f"?action=approve&token={task_token}"
        )
        reject_url = (
            f"{self._backend_url}/api/approvals/{incident_id}"
            f"?action=reject&token={task_token}"
        )

        preview = diff_preview[:500] + ("..." if len(diff_preview) > 500 else "")

        body = f"""Sovereign-SRE has detected an incident and proposes a fix.

Incident ID:  {incident_id}
Root Cause:   {summary}

Proposed Fix Preview:
──────────────────────
{preview}
──────────────────────

To APPROVE this fix (Sovereign-SRE will apply the patch):
{approve_url}

To REJECT this fix (incident will be marked unresolved):
{reject_url}

⚠️  This approval link expires in 1 hour.

──
Sovereign-SRE Autonomous Healing System
"""

        self._sns().publish(
            TopicArn=self._topic_arn,
            Subject=f"[Sovereign-SRE] Action required: {incident_id}",
            Message=body,
        )

    def subscribe_email(self, email: str) -> str:
        """Subscribe an email address to the approval topic."""
        resp = self._sns().subscribe(
            TopicArn=self._topic_arn,
            Protocol="email",
            Endpoint=email,
        )
        return resp.get("SubscriptionArn", "pending-confirmation")
