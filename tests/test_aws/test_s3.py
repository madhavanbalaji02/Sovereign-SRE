"""Tests for aws/s3/artifact_store.py"""

import boto3
import pytest
from moto import mock_aws

from tests.test_aws.conftest import ACCOUNT_ID, REGION

BUCKET = f"sovereign-sre-artifacts-{ACCOUNT_ID}"


@mock_aws
def test_save_and_retrieve_diff(aws_env):
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET)

    from aws.s3.artifact_store import ArtifactStore
    store = ArtifactStore(bucket=BUCKET, region=REGION)

    key, url = store.save_diff("inc-001", "@@ -1 +1 @@\n-old\n+new\n")
    assert key == "incidents/inc-001/fix.diff"
    assert "inc-001" in url or url.startswith("https://")

    content = store.get_object_text(key)
    assert "old" in content


@mock_aws
def test_save_report(aws_env):
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET)

    from aws.s3.artifact_store import ArtifactStore
    store = ArtifactStore(bucket=BUCKET, region=REGION)

    key = store.save_report("inc-002", {"status": "resolved", "confidence": 0.9})
    assert key == "incidents/inc-002/report.json"


@mock_aws
def test_save_log_snapshot(aws_env):
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET)

    from aws.s3.artifact_store import ArtifactStore
    store = ArtifactStore(bucket=BUCKET, region=REGION)

    key = store.save_log_snapshot("inc-003", ["ERROR: OOM", "INFO: restart"])
    assert key == "incidents/inc-003/logs.json"


@mock_aws
def test_list_incident_artifacts(aws_env):
    s3 = boto3.client("s3", region_name=REGION)
    s3.create_bucket(Bucket=BUCKET)

    from aws.s3.artifact_store import ArtifactStore
    store = ArtifactStore(bucket=BUCKET, region=REGION)

    store.save_diff("inc-004", "diff content")
    store.save_report("inc-004", {"ok": True})
    keys = store.list_incident_artifacts("inc-004")
    assert len(keys) == 2
