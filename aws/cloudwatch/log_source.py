"""
CloudWatch Log Source
=====================
Pull logs from CloudWatch Log Groups for the agent's LogMonitor node.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

import boto3

from aws.config import CW_LOG_GROUP, REGION


class CloudWatchLogSource:
    DEFAULT_LOG_GROUPS = [
        CW_LOG_GROUP,
        "/aws/lambda/sovereign-sre-remediation-trigger",
    ]

    def __init__(self, region: str = REGION):
        self._region = region
        self._client: Optional[object] = None

    def _logs(self):
        if self._client is None:
            self._client = boto3.client("logs", region_name=self._region)
        return self._client

    def pull_recent_logs(
        self,
        log_group: str = CW_LOG_GROUP,
        minutes: int = 5,
        filter_pattern: str = "ERROR",
        limit: int = 100,
    ) -> list[str]:
        """Return recent filtered log messages from a CloudWatch Log Group."""
        start_ms = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp() * 1000)

        messages: list[str] = []
        try:
            paginator = self._logs().get_paginator("filter_log_events")
            for page in paginator.paginate(
                logGroupName=log_group,
                startTime=start_ms,
                filterPattern=filter_pattern,
                PaginationConfig={"MaxItems": limit},
            ):
                for event in page.get("events", []):
                    messages.append(event.get("message", "").strip())
        except self._logs().exceptions.ResourceNotFoundException:
            pass  # log group doesn't exist yet
        except Exception as e:
            print(f"[CWLogSource] pull_recent_logs error ({log_group}): {e}")

        return messages

    def pull_all_default_groups(self, minutes: int = 5) -> list[str]:
        """Pull ERROR logs from all default log groups."""
        messages = []
        for group in self.DEFAULT_LOG_GROUPS:
            messages.extend(self.pull_recent_logs(log_group=group, minutes=minutes))
        return messages

    def tail_log_stream(
        self,
        log_group: str,
        stream_name: str,
        poll_interval: float = 2.0,
    ) -> Iterator[str]:
        """Yield log events from a stream in near-real-time (blocking generator)."""
        next_token = None
        while True:
            kwargs = {"logGroupName": log_group, "logStreamName": stream_name}
            if next_token:
                kwargs["nextToken"] = next_token
            try:
                resp = self._logs().get_log_events(**kwargs)
                for event in resp.get("events", []):
                    yield event.get("message", "").strip()
                next_token = resp.get("nextForwardToken")
            except Exception:
                pass
            time.sleep(poll_interval)

    def ensure_log_group(self, log_group: str = CW_LOG_GROUP) -> None:
        """Create log group if it doesn't exist."""
        try:
            self._logs().create_log_group(logGroupName=log_group)
        except self._logs().exceptions.ResourceAlreadyExistsException:
            pass
