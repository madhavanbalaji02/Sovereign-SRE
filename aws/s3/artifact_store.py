"""
S3 Artifact Store
=================
Stores diffs, reports, and log snapshots.
Bucket: sovereign-sre-artifacts-{account_id}
Lifecycle: objects deleted after 30 days.

# COST SAFE: S3 <5GB = $0, presigned URLs are free
"""


from __future__ import annotations
import json
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from aws.config import S3_BUCKET, REGION


class ArtifactStore:
    def __init__(self, bucket: str = S3_BUCKET, region: str = REGION):
        self._bucket = bucket
        self._region = region
        self._client: Optional[object] = None

    def _s3(self):
        if self._client is None:
            self._client = boto3.client("s3", region_name=self._region)
        return self._client

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def save_diff(self, incident_id: str, diff: str) -> tuple[str, str]:
        """Save a unified diff; return (s3_key, presigned_url)."""
        key = f"incidents/{incident_id}/fix.diff"
        self._s3().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=diff.encode("utf-8"),
            ContentType="text/plain",
        )
        url = self.get_presigned_url(key)
        return key, url

    def save_report(self, incident_id: str, report: dict) -> str:
        """Save a JSON report; return s3_key."""
        key = f"incidents/{incident_id}/report.json"
        self._s3().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(report, indent=2, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        return key

    def save_log_snapshot(self, incident_id: str, logs: list[str]) -> str:
        """Save a log snapshot; return s3_key."""
        key = f"incidents/{incident_id}/logs.json"
        self._s3().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps({"logs": logs}, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
        return key

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_presigned_url(self, s3_key: str, expiry_seconds: int = 86400) -> str:
        return self._s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )

    def list_incident_artifacts(self, incident_id: str) -> list[str]:
        prefix = f"incidents/{incident_id}/"
        resp = self._s3().list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]

    def get_object_text(self, s3_key: str) -> str:
        resp = self._s3().get_object(Bucket=self._bucket, Key=s3_key)
        return resp["Body"].read().decode("utf-8")
