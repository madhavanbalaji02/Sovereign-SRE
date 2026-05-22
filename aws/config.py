"""
AWS Resource Configuration
==========================
All resource names, ARNs, and region constants for Sovereign-SRE.
Import from here — never hardcode names in service files.
"""

import os

# ---------------------------------------------------------------------------
# Core AWS settings
# ---------------------------------------------------------------------------
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")  # filled at runtime by setup.py

# ---------------------------------------------------------------------------
# Resource names (stable identifiers — safe to hardcode)
# ---------------------------------------------------------------------------
IAM_ROLE_NAME = "sovereign-sre-execution-role"

S3_BUCKET = os.environ.get("S3_BUCKET", f"sovereign-sre-artifacts-{ACCOUNT_ID}")
S3_LIFECYCLE_DAYS = 30

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "sovereign-sre-incidents")
DYNAMODB_TTL_DAYS = 90

SNS_TOPIC_NAME = "sovereign-sre-approvals"
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "")

CW_LOG_GROUP = "/sovereign-sre/incidents"
CW_NAMESPACE = "SovereignSRE"

FIREHOSE_STREAM = os.environ.get("FIREHOSE_STREAM", "sovereign-sre-logs")

RDS_INSTANCE_ID = "sovereign-sre-db"
RDS_DB_NAME = "sovereignsre"
RDS_USER = "sreadmin"
RDS_PORT = 5432

LAMBDA_FUNCTION_NAME = os.environ.get("LAMBDA_FUNCTION_NAME", "sovereign-sre-remediation-trigger")

STATE_MACHINE_NAME = "sovereign-sre-pipeline"
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")

EVENTBRIDGE_RULE_NAME = "sovereign-sre-alarm-trigger"

# ---------------------------------------------------------------------------
# SSM parameter paths
# ---------------------------------------------------------------------------
SSM_PREFIX = "/sovereign-sre"
SSM_KEYS = {
    "groq-api-key":          f"{SSM_PREFIX}/groq-api-key",
    "anthropic-api-key":     f"{SSM_PREFIX}/anthropic-api-key",
    "github-token":          f"{SSM_PREFIX}/github-token",
    "rds-connection-string": f"{SSM_PREFIX}/rds-connection-string",
    "backend-url":           f"{SSM_PREFIX}/backend-url",
    "sns-topic-arn":         f"{SSM_PREFIX}/sns-topic-arn",
}

# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------
BEDROCK_ENABLED = os.environ.get("BEDROCK_ENABLED", "true").lower() == "true"
BEDROCK_DEFAULT_MODEL = os.environ.get("BEDROCK_DEFAULT_MODEL", "haiku")
BEDROCK_FALLBACK_TO_GROQ = os.environ.get("BEDROCK_FALLBACK_TO_OLLAMA", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Backend URL (used by Lambda to notify the real-time WebSocket layer)
# ---------------------------------------------------------------------------
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
