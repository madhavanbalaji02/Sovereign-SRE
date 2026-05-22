"""Tests for aws/dynamodb/incident_store.py"""

import boto3
import pytest
from moto import mock_aws

from tests.test_aws.conftest import REGION

TABLE = "sovereign-sre-incidents"


def _make_table():
    ddb = boto3.client("dynamodb", region_name=REGION)
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


@mock_aws
def test_save_and_get_incident(aws_env):
    _make_table()
    from aws.dynamodb.incident_store import IncidentStore
    store = IncidentStore(table_name=TABLE, region=REGION)

    incident_id = store.save_incident({
        "status": "running",
        "trigger_source": "test",
        "alarm_name": "sovereign-sre-ErrorRate",
    })

    result = store.get_incident(incident_id)
    assert result is not None
    assert result["status"] == "running"
    assert result["trigger_source"] == "test"


@mock_aws
def test_update_incident(aws_env):
    _make_table()
    from aws.dynamodb.incident_store import IncidentStore
    store = IncidentStore(table_name=TABLE, region=REGION)

    incident_id = store.save_incident({"status": "running"})
    item = store.get_incident(incident_id)

    store.update_incident(incident_id, item["timestamp"], status="resolved")
    updated = store.get_incident(incident_id)
    assert updated["status"] == "resolved"


@mock_aws
def test_list_incidents(aws_env):
    _make_table()
    from aws.dynamodb.incident_store import IncidentStore
    store = IncidentStore(table_name=TABLE, region=REGION)

    for i in range(3):
        store.save_incident({"status": "resolved", "trigger_source": f"test-{i}"})

    incidents = store.list_incidents(limit=10)
    assert len(incidents) == 3


@mock_aws
def test_agent_state_round_trip(aws_env):
    _make_table()
    from aws.dynamodb.incident_store import IncidentStore
    store = IncidentStore(table_name=TABLE, region=REGION)

    state_data = {"run_id": "abc", "status": "running", "issues": ["OOM"]}
    store.save_agent_state("run-123", state_data)

    retrieved = store.get_agent_state("run-123")
    assert retrieved is not None
    assert retrieved["run_id"] == "abc"
    assert "OOM" in retrieved["issues"]
