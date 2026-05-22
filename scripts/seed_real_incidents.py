"""
Step 5: Seed real incidents from data/incidents_with_fixes.json into DynamoDB + S3.

- Clears existing seeded/test incidents
- Inserts 15 real incidents with IDs: REAL-GAIA-001, REAL-AIOPS-007, etc.
- Uploads report.json, timeseries.json, fix.diff to S3

Usage:
    python3 scripts/seed_real_incidents.py
"""

import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).parent.parent
INPUT_FILE = ROOT / "data" / "incidents_with_fixes.json"

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "sovereign-sre-incidents")
S3_BUCKET = os.environ.get("S3_BUCKET", "sovereign-sre-artifacts-574772738370")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")


def float_to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(round(obj, 6)))
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def clear_seeded(table, source_values: list[str]) -> int:
    """Delete items where trigger_source matches seed sources."""
    deleted = 0
    for src in source_values:
        response = table.scan(
            FilterExpression="trigger_source = :src",
            ExpressionAttributeValues={":src": src},
        )
        for item in response.get("Items", []):
            table.delete_item(Key={"incident_id": item["incident_id"]})
            deleted += 1
    return deleted


def build_incident_id(inc: dict, idx: int) -> str:
    src = inc["source"].upper()  # GAIA or AIOPSARENA → AIOPS
    prefix = "GAIA" if src == "GAIA" else "AIOPS"
    return f"REAL-{prefix}-{idx:03d}"


def build_alarm_name(inc: dict) -> str:
    svc = inc["service"].replace("_", "-")
    atype = inc["anomaly_type"].replace("_", "-")
    return f"{svc}-{atype}-critical"


def main() -> None:
    print("=" * 60)
    print("STEP 5 — SEEDING REAL INCIDENTS TO AWS")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"✗ {INPUT_FILE} not found — run previous steps first", file=sys.stderr)
        sys.exit(1)

    incidents = json.loads(INPUT_FILE.read_text())
    print(f"  Loaded {len(incidents)} incidents from {INPUT_FILE}")

    import boto3

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    s3 = boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    table = dynamodb.Table(TABLE_NAME)

    # Clear old seeded data
    print(f"\n→ Clearing old seeded incidents from {TABLE_NAME}...")
    seed_sources = ["seed", "manual_test", "gaia_dataset", "aiopsarena_dataset"]
    deleted = clear_seeded(table, seed_sources)
    print(f"  Deleted {deleted} old items")

    # Build source index counters
    gaia_count = 0
    aiops_count = 0

    db_count = 0
    s3_count = 0

    for i, inc in enumerate(incidents):
        is_gaia = inc["source"] == "gaia"
        if is_gaia:
            gaia_count += 1
            incident_id = f"REAL-GAIA-{gaia_count:03d}"
            trigger_source = "gaia_dataset"
        else:
            aiops_count += 1
            incident_id = f"REAL-AIOPS-{aiops_count:03d}"
            trigger_source = "aiopsarena_dataset"

        # First 12 resolved, last 3 open
        is_resolved = i < 12
        status = "resolved" if is_resolved else "open"
        approval_status = "approved" if is_resolved else "pending"
        resolution_time_ms = int(inc.get("duration_seconds", 300) * 1000 * 0.6) if is_resolved else None

        alarm_name = build_alarm_name(inc)

        # Build DynamoDB item (timeseries excluded — too large, goes to S3)
        item = {
            "incident_id": incident_id,
            "alarm_name": alarm_name,
            "trigger_source": trigger_source,
            "status": status,
            "approval_status": approval_status,
            "timestamp": inc.get("timestamp", datetime.utcnow().isoformat()),
            # Real data fields
            "source_dataset": inc["source"],
            "service": inc["service"],
            "anomaly_type": inc["anomaly_type"],
            "severity": inc["severity"],
            "duration_seconds": str(inc.get("duration_seconds", 300)),
            "affected_containers": ", ".join(inc.get("affected_containers", [inc["service"]])),
            "raw_log_line": inc.get("raw_log_line", "")[:500],
            # Bedrock-generated fields
            "root_cause": inc.get("root_cause", ""),
            "proposed_fix": "; ".join(inc.get("resolution_steps", [])),
            "confidence": str(round(inc.get("confidence", 0.88), 2)),
            "bedrock_model_used": inc.get("bedrock_model", "us.anthropic.claude-haiku-4-5-20251001-v1:0"),
            "tokens_used": str(inc.get("tokens_used", 0)),
            "cost_usd": str(round(inc.get("cost_usd", 0.0), 6)),
            "diff_preview": inc.get("diff", ""),
            # Metrics
            "metric_baseline": str(round(float(inc.get("metric_baseline") or 40.0), 2)),
            "metric_peak": str(round(float(inc.get("metric_peak") or 80.0), 2)),
            "spike_ratio": str(round(float(inc.get("spike_ratio") or 2.0), 3)),
        }

        if resolution_time_ms is not None:
            item["resolution_time_ms"] = str(resolution_time_ms)

        # Write to DynamoDB
        try:
            table.put_item(Item=item)
            print(f"  ✓ DynamoDB: {incident_id}  [{status}]  {alarm_name[:50]}")
            db_count += 1
        except Exception as e:
            print(f"  ✗ DynamoDB: {incident_id} — {e}")

        # Write to S3
        s3_prefix = f"incidents/{incident_id}"
        try:
            # report.json (full incident without large timeseries)
            report = {k: v for k, v in {**inc, "incident_id": incident_id}.items()
                     if k != "timeseries"}
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f"{s3_prefix}/report.json",
                Body=json.dumps(report, indent=2),
                ContentType="application/json",
            )

            # timeseries.json
            ts_data = {"incident_id": incident_id, "points": inc.get("timeseries", [])}
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f"{s3_prefix}/timeseries.json",
                Body=json.dumps(ts_data, indent=2),
                ContentType="application/json",
            )

            # fix.diff
            diff_content = inc.get("diff", "# No diff available")
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=f"{s3_prefix}/fix.diff",
                Body=diff_content.encode(),
                ContentType="text/plain",
            )

            s3_count += 3
        except Exception as e:
            print(f"  ✗ S3: {incident_id} — {e}")

    print(f"\n✓ Seeded {db_count} incidents to DynamoDB ({TABLE_NAME})")
    print(f"✓ Uploaded {s3_count} artifacts to S3 (s3://{S3_BUCKET}/incidents/)")
    print(f"\n  GAIA incidents:    {gaia_count}")
    print(f"  AIOpsArena incidents: {aiops_count}")

    # Compute total cost
    total_cost = sum(float(inc.get("cost_usd", 0)) for inc in incidents)
    print(f"\n  Total Bedrock cost: ${total_cost:.4f}")


if __name__ == "__main__":
    env_path = ROOT / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
    main()
