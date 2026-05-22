"""
Seed 4 realistic incidents into DynamoDB for the Sovereign-SRE dashboard.

Usage:
    python3 scripts/seed_incidents.py

Requires:
    pip install boto3
    AWS credentials configured (env vars or ~/.aws/credentials)
    AWS_REGION env var (defaults to us-east-1)

The table name is read from TABLE_NAME env var (defaults to sovereign-sre-incidents).
"""

import boto3
import os
import json
from decimal import Decimal
from datetime import datetime

TABLE_NAME = os.environ.get("TABLE_NAME", "sovereign-sre-incidents")
REGION = os.environ.get("AWS_REGION", "us-east-1")

INCIDENTS = [
    {
        "incident_id": "INC-2025-001",
        "alarm_name": "payments-service-memory-critical",
        "root_cause": (
            "Memory leak in payment processor connection pool. "
            "Unclosed JDBC connections accumulating over 6 hours."
        ),
        "proposed_fix": (
            "Set connection pool max-size=20, added finally block "
            "to ensure connection.close() on all code paths."
        ),
        "confidence": "0.94",
        "status": "resolved",
        "approval_status": "approved",
        "resolution_time_ms": "3420",
        "bedrock_model_used": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "tokens_used": "2480",
        "cost_usd": "0.00105",
        "timestamp": "2025-01-15T10:23:00Z",
        "diff_preview": (
            "- connection_pool = ConnectionPool(max_size=100)\n"
            "+ connection_pool = ConnectionPool(max_size=20,\n"
            "+     timeout=30, validate_on_checkout=True)\n"
            "+\n"
            "+ def process_payment(self, data):\n"
            "+     conn = self.pool.get_connection()\n"
            "+     try:\n"
            "+         return self._execute(conn, data)\n"
            "+     finally:\n"
            "+         conn.close()  # guaranteed cleanup"
        ),
    },
    {
        "incident_id": "INC-2025-002",
        "alarm_name": "api-gateway-5xx-rate-critical",
        "root_cause": (
            "Downstream ML inference endpoint timing out after model update "
            "increased p95 latency from 180ms to 4200ms."
        ),
        "proposed_fix": (
            "Added circuit breaker with 2s timeout + fallback to cached "
            "predictions for non-critical requests."
        ),
        "confidence": "0.91",
        "status": "resolved",
        "approval_status": "approved",
        "resolution_time_ms": "5100",
        "bedrock_model_used": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "tokens_used": "1940",
        "cost_usd": "0.00082",
        "timestamp": "2025-01-18T14:07:00Z",
    },
    {
        "incident_id": "INC-2025-003",
        "alarm_name": "worker-node-disk-utilization-critical",
        "root_cause": (
            "Log rotation disabled after last deployment. "
            "/var/log growing at 2.3 GB/day, disk 94% full."
        ),
        "proposed_fix": (
            "Re-enabled logrotate, set 7-day retention, "
            "compressed old logs, freed 47 GB immediately."
        ),
        "confidence": "0.98",
        "status": "resolved",
        "approval_status": "approved",
        "resolution_time_ms": "1890",
        "bedrock_model_used": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "tokens_used": "1120",
        "cost_usd": "0.00048",
        "timestamp": "2025-01-22T09:45:00Z",
    },
    {
        "incident_id": "INC-2025-004",
        "alarm_name": "llm-eval-faithfulness-below-threshold",
        "root_cause": (
            "Faithfulness score dropped from 0.89 to 0.61 after prompt template update. "
            "RAGAS detects hallucination rate 3x above baseline on financial domain queries."
        ),
        "proposed_fix": (
            "Roll back prompt template to v2.3, re-run eval harness "
            "on affected query categories."
        ),
        "confidence": "0.87",
        "status": "open",
        "approval_status": "pending",
        "timestamp": "2025-01-24T16:30:00Z",
    },
]


def seed(table_name: str, region: str) -> None:
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)

    print(f"Seeding {len(INCIDENTS)} incidents into {table_name} ({region})...")

    for inc in INCIDENTS:
        table.put_item(Item=inc)
        print(f"  ✓  {inc['incident_id']}  [{inc['status']}]  {inc['alarm_name']}")

    print(f"\nDone. {len(INCIDENTS)} incidents written.")


if __name__ == "__main__":
    seed(TABLE_NAME, REGION)
