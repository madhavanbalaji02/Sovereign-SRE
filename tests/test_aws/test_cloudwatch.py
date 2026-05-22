"""Tests for aws/cloudwatch/metrics.py, log_source.py, and alarms.py"""

import boto3
import pytest
from moto import mock_aws

from tests.test_aws.conftest import REGION

NAMESPACE = "SovereignSRE"


@mock_aws
def test_push_metric(aws_env):
    from aws.cloudwatch.metrics import SREMetrics
    metrics = SREMetrics(namespace=NAMESPACE, region=REGION)
    # Should not raise
    metrics.push("TestMetric", 1.0)
    metrics.push("TestMetric", 5.0, unit="Count", dimensions=[
        {"Name": "Service", "Value": "backend"}
    ])


@mock_aws
def test_record_pipeline_start(aws_env):
    from aws.cloudwatch.metrics import SREMetrics
    metrics = SREMetrics(namespace=NAMESPACE, region=REGION)
    metrics.record_pipeline_start("test-incident-001")


@mock_aws
def test_record_pipeline_complete(aws_env):
    from aws.cloudwatch.metrics import SREMetrics
    metrics = SREMetrics(namespace=NAMESPACE, region=REGION)
    metrics.record_pipeline_complete("test-incident-002", duration_ms=3500.0, success=True)
    metrics.record_pipeline_complete("test-incident-003", duration_ms=1200.0, success=False)


@mock_aws
def test_record_bedrock_tokens(aws_env):
    from aws.cloudwatch.metrics import SREMetrics
    metrics = SREMetrics(namespace=NAMESPACE, region=REGION)
    metrics.record_bedrock_tokens(1000, 500, "anthropic.claude-haiku-4-5-20251001")


@mock_aws
def test_create_alarms(aws_env):
    # Create a fake SNS topic first
    sns = boto3.client("sns", region_name=REGION)
    topic_arn = sns.create_topic(Name="sovereign-sre-approvals")["TopicArn"]

    from aws.cloudwatch.alarms import AlarmManager
    manager = AlarmManager(region=REGION, sns_topic_arn=topic_arn)
    manager.create_standard_alarms()

    alarms = manager.list_alarms()
    alarm_names = [a["AlarmName"] for a in alarms]
    assert "sovereign-sre-ErrorRate" in alarm_names
    assert "sovereign-sre-PipelineFailureRate" in alarm_names


@mock_aws
def test_pull_logs_missing_group(aws_env):
    """pull_recent_logs should not raise when log group doesn't exist."""
    from aws.cloudwatch.log_source import CloudWatchLogSource
    source = CloudWatchLogSource(region=REGION)
    logs = source.pull_recent_logs(log_group="/does-not-exist")
    assert isinstance(logs, list)


@mock_aws
def test_ensure_log_group(aws_env):
    from aws.cloudwatch.log_source import CloudWatchLogSource
    source = CloudWatchLogSource(region=REGION)
    source.ensure_log_group("/sovereign-sre/incidents")
    # Calling again should not raise (idempotent)
    source.ensure_log_group("/sovereign-sre/incidents")
