"""
Kinesis Firehose Log Ingestor
==============================
Sends logs to the sovereign-sre-logs Firehose delivery stream.
Destination: S3 s3://sovereign-sre-artifacts/firehose-logs/

Note: Firehose buffers 60s minimum.
      Use CloudWatch Logs (log_source.py) for real-time <60s needs.

# COST SAFE: Firehose <500K records = $0 (first month)
# SRE log volume: ~10MB/day = ~300MB/month = ~$0.009/month. Essentially free.
"""


from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import Optional

import boto3

from aws.config import FIREHOSE_STREAM, S3_BUCKET, REGION


class FirehoseLogIngestor:
    MAX_BATCH_RECORDS = 500
    MAX_BATCH_BYTES = 4 * 1024 * 1024  # 4 MB

    def __init__(
        self,
        stream_name: str = FIREHOSE_STREAM,
        s3_bucket: str = S3_BUCKET,
        region: str = REGION,
    ):
        self._stream = stream_name
        self._bucket = s3_bucket
        self._region = region
        self._fh: Optional[object] = None
        self._s3: Optional[object] = None

    def _firehose(self):
        if self._fh is None:
            self._fh = boto3.client("firehose", region_name=self._region)
        return self._fh

    def _s3_client(self):
        if self._s3 is None:
            self._s3 = boto3.client("s3", region_name=self._region)
        return self._s3

    def put_log_batch(self, logs: list[str]) -> None:
        """Send log lines to Firehose (batches up to 500 records or 4MB)."""
        if not logs:
            return

        records = [{"Data": (line + "\n").encode("utf-8")} for line in logs]

        # Chunk into Firehose-legal batches
        for i in range(0, len(records), self.MAX_BATCH_RECORDS):
            chunk = records[i: i + self.MAX_BATCH_RECORDS]
            # Trim if byte limit exceeded
            batch, size = [], 0
            for r in chunk:
                size += len(r["Data"])
                if size > self.MAX_BATCH_BYTES:
                    break
                batch.append(r)

            try:
                self._firehose().put_record_batch(
                    DeliveryStreamName=self._stream,
                    Records=batch,
                )
            except Exception as e:
                print(f"[Firehose] put_record_batch error: {e}")

    def tail_recent_logs(self, minutes: int = 5) -> list[str]:
        """
        Read latest Firehose output from S3.
        Firehose buffers ~60s, so recent events may not appear yet.
        Use CloudWatch Logs for real-time needs.
        """
        from datetime import timedelta
        prefix_base = "firehose-logs/"
        messages: list[str] = []

        now = datetime.now(timezone.utc)
        # Check last N minutes' worth of S3 prefixes
        for delta in range(minutes + 1):
            dt = now - timedelta(minutes=delta)
            prefix = (
                f"{prefix_base}"
                f"year={dt.year}/"
                f"month={dt.month:02d}/"
                f"day={dt.day:02d}/"
                f"hour={dt.hour:02d}/"
            )
            try:
                resp = self._s3_client().list_objects_v2(
                    Bucket=self._bucket, Prefix=prefix
                )
                for obj in resp.get("Contents", []):
                    body = self._s3_client().get_object(
                        Bucket=self._bucket, Key=obj["Key"]
                    )["Body"].read().decode("utf-8", errors="replace")
                    messages.extend(line for line in body.splitlines() if line.strip())
            except Exception:
                pass

        return messages[-500:]  # cap to most recent 500 lines
