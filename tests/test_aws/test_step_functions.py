"""Tests for aws/step_functions/executor.py"""

import json
import boto3
import pytest
from moto import mock_aws

from tests.test_aws.conftest import REGION, ACCOUNT_ID

SM_NAME = "sovereign-sre-pipeline"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/sovereign-sre-execution-role"


def _create_state_machine(sf_client) -> str:
    """Create a minimal state machine for testing."""
    definition = json.dumps({
        "Comment": "Test",
        "StartAt": "Done",
        "States": {"Done": {"Type": "Succeed"}},
    })
    resp = sf_client.create_state_machine(
        name=SM_NAME,
        definition=definition,
        roleArn=ROLE_ARN,
        type="STANDARD",
    )
    return resp["stateMachineArn"]


@mock_aws
def test_start_execution(aws_env, monkeypatch):
    iam = boto3.client("iam", region_name=REGION)
    iam.create_role(
        RoleName="sovereign-sre-execution-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"},
                           "Action": "sts:AssumeRole"}],
        }),
    )
    sf = boto3.client("stepfunctions", region_name=REGION)
    sm_arn = _create_state_machine(sf)

    monkeypatch.setenv("STATE_MACHINE_ARN", sm_arn)
    from aws.step_functions.executor import PipelineExecutor
    executor = PipelineExecutor(state_machine_arn=sm_arn, region=REGION)

    execution_arn = executor.start_execution({"logs": ["ERROR: test"], "anomaly_detected": True})
    assert "arn:aws:states" in execution_arn


@mock_aws
def test_get_status(aws_env, monkeypatch):
    iam = boto3.client("iam", region_name=REGION)
    iam.create_role(
        RoleName="sovereign-sre-execution-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"},
                           "Action": "sts:AssumeRole"}],
        }),
    )
    sf = boto3.client("stepfunctions", region_name=REGION)
    sm_arn = _create_state_machine(sf)

    from aws.step_functions.executor import PipelineExecutor
    executor = PipelineExecutor(state_machine_arn=sm_arn, region=REGION)
    execution_arn = executor.start_execution({"anomaly_detected": False})
    status = executor.get_status(execution_arn)

    assert "status" in status
    assert status["status"] in ("RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED")


@mock_aws
def test_list_executions(aws_env):
    iam = boto3.client("iam", region_name=REGION)
    iam.create_role(
        RoleName="sovereign-sre-execution-role",
        AssumeRolePolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"},
                           "Action": "sts:AssumeRole"}],
        }),
    )
    sf = boto3.client("stepfunctions", region_name=REGION)
    sm_arn = _create_state_machine(sf)

    from aws.step_functions.executor import PipelineExecutor
    executor = PipelineExecutor(state_machine_arn=sm_arn, region=REGION)
    executor.start_execution({"anomaly_detected": False})
    executor.start_execution({"anomaly_detected": True})

    executions = executor.list_executions()
    assert len(executions) >= 1
