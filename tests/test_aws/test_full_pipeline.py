"""
End-to-end pipeline test with all AWS services mocked.

Flow: CloudWatch alarm → Lambda trigger → Step Functions → DynamoDB save
      + S3 artifact store + CloudWatch metrics
"""

import json
import boto3
import pytest
from moto import mock_aws

from tests.test_aws.conftest import REGION, ACCOUNT_ID

BUCKET = f"sovereign-sre-artifacts-{ACCOUNT_ID}"
TABLE = "sovereign-sre-incidents"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/sovereign-sre-execution-role"


def _bootstrap_aws(s3, ddb, sns, iam, sf):
    """Create all required mocked resources."""
    # S3
    s3.create_bucket(Bucket=BUCKET)

    # DynamoDB
    ddb.create_table(
        TableName=TABLE,
        KeySchema=[
            {"AttributeName": "incident_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "incident_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "status-index",
            "KeySchema": [
                {"AttributeName": "status", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
        }],
        BillingMode="PAY_PER_REQUEST",
    )

    # SNS
    topic_arn = sns.create_topic(Name="sovereign-sre-approvals")["TopicArn"]

    # IAM role
    iam.create_role(
        RoleName="sovereign-sre-execution-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"},
                           "Action": "sts:AssumeRole"}],
        }),
    )

    # Step Functions
    sm_arn = sf.create_state_machine(
        name="sovereign-sre-pipeline",
        definition=json.dumps({
            "Comment": "Test pipeline",
            "StartAt": "Done",
            "States": {"Done": {"Type": "Succeed"}},
        }),
        roleArn=ROLE_ARN,
        type="STANDARD",
    )["stateMachineArn"]

    return topic_arn, sm_arn


@mock_aws
def test_full_incident_lifecycle(aws_env, monkeypatch):
    """Simulate: save incident → update → retrieve → save artifacts → list."""
    s3 = boto3.client("s3", region_name=REGION)
    ddb = boto3.client("dynamodb", region_name=REGION)
    sns = boto3.client("sns", region_name=REGION)
    iam = boto3.client("iam", region_name=REGION)
    sf = boto3.client("stepfunctions", region_name=REGION)

    topic_arn, sm_arn = _bootstrap_aws(s3, ddb, sns, iam, sf)
    monkeypatch.setenv("STATE_MACHINE_ARN", sm_arn)
    monkeypatch.setenv("SNS_TOPIC_ARN", topic_arn)

    # 1. Save incident
    from aws.dynamodb.incident_store import IncidentStore
    store = IncidentStore(table_name=TABLE, region=REGION)
    incident_id = store.save_incident({
        "status": "running",
        "trigger_source": "cloudwatch_alarm",
        "alarm_name": "sovereign-sre-ErrorRate",
    })

    # 2. Metrics push
    from aws.cloudwatch.metrics import SREMetrics
    metrics = SREMetrics(region=REGION)
    metrics.record_pipeline_start(incident_id)

    # 3. Save artifacts
    from aws.s3.artifact_store import ArtifactStore
    artifact_store = ArtifactStore(bucket=BUCKET, region=REGION)
    diff_key, _ = artifact_store.save_diff(incident_id, "@@ -1 +1 @@\n-broken\n+fixed\n")
    log_key = artifact_store.save_log_snapshot(incident_id, ["ERROR: OOMKilled"])

    # 4. Update incident to resolved
    item = store.get_incident(incident_id)
    assert item is not None
    store.update_incident(incident_id, item["timestamp"], status="resolved", diff_s3_key=diff_key)

    # 5. Verify final state
    final = store.get_incident(incident_id)
    assert final["status"] == "resolved"
    assert final["diff_s3_key"] == diff_key

    # 6. Verify artifacts in S3
    keys = artifact_store.list_incident_artifacts(incident_id)
    assert len(keys) == 2

    # 7. Start Step Functions execution
    from aws.step_functions.executor import PipelineExecutor
    executor = PipelineExecutor(state_machine_arn=sm_arn, region=REGION)
    exec_arn = executor.start_execution({"incident_id": incident_id, "anomaly_detected": True})
    assert "arn:aws:states" in exec_arn

    status = executor.get_status(exec_arn)
    assert status["status"] in ("RUNNING", "SUCCEEDED")


@mock_aws
def test_lambda_handler_starts_execution(aws_env, monkeypatch):
    """Lambda handler should call sf.start_execution and not crash."""
    iam = boto3.client("iam", region_name=REGION)
    sf_client = boto3.client("stepfunctions", region_name=REGION)

    iam.create_role(
        RoleName="sovereign-sre-execution-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"},
                           "Action": "sts:AssumeRole"}],
        }),
    )
    sm_arn = sf_client.create_state_machine(
        name="sovereign-sre-pipeline",
        definition=json.dumps({
            "Comment": "Test",
            "StartAt": "Done",
            "States": {"Done": {"Type": "Succeed"}},
        }),
        roleArn=ROLE_ARN,
        type="STANDARD",
    )["stateMachineArn"]

    monkeypatch.setenv("STATE_MACHINE_ARN", sm_arn)
    monkeypatch.setenv("BACKEND_URL", "")  # disable backend notification

    event = {
        "time": "2026-05-22T10:00:00Z",
        "detail": {
            "alarmName": "sovereign-sre-ErrorRate",
            "state": {
                "value": "ALARM",
                "reason": "Threshold breached: 6 datapoints > 5",
            },
        },
    }

    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2] / "aws" / "lambda_functions"))
    from remediation_trigger import lambda_handler
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    assert "executionArn" in result
