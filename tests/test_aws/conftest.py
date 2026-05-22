"""
pytest fixtures for AWS service mocking via moto.
All tests that use AWS clients should use the mock_aws fixture.
"""

import os

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Set dummy AWS credentials before any boto3 client is created
# ---------------------------------------------------------------------------
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCOUNT_ID", "123456789012")

REGION = "us-east-1"
ACCOUNT_ID = "123456789012"


@pytest.fixture(scope="function")
def aws_env(monkeypatch):
    """Ensure dummy credentials are set for every test function."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    monkeypatch.setenv("AWS_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("S3_BUCKET", f"sovereign-sre-artifacts-{ACCOUNT_ID}")
    monkeypatch.setenv("DYNAMODB_TABLE", "sovereign-sre-incidents")
    monkeypatch.setenv("SNS_TOPIC_ARN", f"arn:aws:sns:{REGION}:{ACCOUNT_ID}:sovereign-sre-approvals")
    monkeypatch.setenv("STATE_MACHINE_ARN", "")
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("FIREHOSE_STREAM", "sovereign-sre-logs")


@pytest.fixture(scope="function")
def s3_bucket(aws_env):
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(Bucket=f"sovereign-sre-artifacts-{ACCOUNT_ID}")
        yield f"sovereign-sre-artifacts-{ACCOUNT_ID}"


@pytest.fixture(scope="function")
def dynamodb_table(aws_env):
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name=REGION)
        ddb.create_table(
            TableName="sovereign-sre-incidents",
            KeySchema=[
                {"AttributeName": "incident_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "incident_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "status-index",
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield "sovereign-sre-incidents"


@pytest.fixture(scope="function")
def sns_topic(aws_env):
    with mock_aws():
        sns = boto3.client("sns", region_name=REGION)
        resp = sns.create_topic(Name="sovereign-sre-approvals")
        yield resp["TopicArn"]
