"""
AWS Teardown — destroys all Sovereign-SRE resources safely
===========================================================
Usage:
    python aws/teardown.py [--yes]

Asks for confirmation unless --yes flag is passed.
RDS deletion does NOT create a final snapshot (dev/test resource).
"""

import sys
import time

import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.prompt import Confirm

console = Console()
REGION = __import__("os").environ.get("AWS_DEFAULT_REGION", "us-east-1")

_sts = boto3.client("sts", region_name=REGION)
ACCOUNT_ID = _sts.get_caller_identity()["Account"]

S3_BUCKET = f"sovereign-sre-artifacts-{ACCOUNT_ID}"
DYNAMODB_TABLE = "sovereign-sre-incidents"
SNS_TOPIC_NAME = "sovereign-sre-approvals"
CW_LOG_GROUP = "/sovereign-sre/incidents"
FIREHOSE_STREAM = "sovereign-sre-logs"
LAMBDA_NAME = "sovereign-sre-remediation-trigger"
STATE_MACHINE_NAME = "sovereign-sre-pipeline"
EVENTBRIDGE_RULE = "sovereign-sre-alarm-trigger"
RDS_INSTANCE_ID = "sovereign-sre-db"
IAM_ROLE_NAME = "sovereign-sre-execution-role"
ALARM_NAMES = [
    "sovereign-sre-ErrorRate",
    "sovereign-sre-PipelineFailureRate",
    "sovereign-sre-ApprovalWaitTime",
]


def _safe(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        console.print(f"  [green]✔[/] Deleted")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchBucket", "ResourceNotFoundException", "DBInstanceNotFound",
                    "ResourceNotFound", "NoSuchEntity"):
            console.print("  [dim]↷ Already gone[/]")
        else:
            console.print(f"  [yellow]⚠ {e}[/]")
    except Exception as e:
        console.print(f"  [yellow]⚠ {e}[/]")


def teardown():
    console.print("[bold red]🗑️  Sovereign-SRE AWS Teardown[/]")
    console.print(f"Region: {REGION} | Account: {ACCOUNT_ID}")
    console.print()

    if "--yes" not in sys.argv:
        if not Confirm.ask("[bold red]This will DESTROY all AWS resources. Continue?[/]"):
            console.print("Aborted.")
            return

    # EventBridge
    console.print("[bold]EventBridge rule[/]")
    from aws.eventbridge.rules import EventBridgeManager
    _safe(EventBridgeManager(region=REGION).delete_rule)

    # Lambda
    console.print("[bold]Lambda function[/]")
    lam = boto3.client("lambda", region_name=REGION)
    _safe(lam.delete_function, FunctionName=LAMBDA_NAME)

    # Step Functions
    console.print("[bold]Step Functions state machine[/]")
    from aws.step_functions.deployer import StateMachineDeployer
    _safe(StateMachineDeployer(region=REGION).delete)

    # CloudWatch alarms
    console.print("[bold]CloudWatch alarms[/]")
    cw = boto3.client("cloudwatch", region_name=REGION)
    _safe(cw.delete_alarms, AlarmNames=ALARM_NAMES)

    # CloudWatch log group
    console.print("[bold]CloudWatch log group[/]")
    logs = boto3.client("logs", region_name=REGION)
    _safe(logs.delete_log_group, logGroupName=CW_LOG_GROUP)

    # Firehose
    console.print("[bold]Kinesis Firehose[/]")
    fh = boto3.client("firehose", region_name=REGION)
    _safe(fh.delete_delivery_stream, DeliveryStreamName=FIREHOSE_STREAM)

    # SNS (delete subscriptions then topic)
    console.print("[bold]SNS topic[/]")
    sns = boto3.client("sns", region_name=REGION)
    topic_arn = f"arn:aws:sns:{REGION}:{ACCOUNT_ID}:{SNS_TOPIC_NAME}"
    try:
        subs = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        for s in subs.get("Subscriptions", []):
            _safe(sns.unsubscribe, SubscriptionArn=s["SubscriptionArn"])
    except Exception:
        pass
    _safe(sns.delete_topic, TopicArn=topic_arn)

    # SSM parameters
    console.print("[bold]SSM parameters[/]")
    ssm = boto3.client("ssm", region_name=REGION)
    for name in [
        "/sovereign-sre/groq-api-key",
        "/sovereign-sre/anthropic-api-key",
        "/sovereign-sre/github-token",
        "/sovereign-sre/rds-connection-string",
        "/sovereign-sre/backend-url",
        "/sovereign-sre/sns-topic-arn",
    ]:
        _safe(ssm.delete_parameter, Name=name)

    # DynamoDB
    console.print("[bold]DynamoDB table[/]")
    ddb = boto3.client("dynamodb", region_name=REGION)
    _safe(ddb.delete_table, TableName=DYNAMODB_TABLE)

    # S3 (empty first)
    console.print("[bold]S3 bucket[/]")
    s3 = boto3.resource("s3", region_name=REGION)
    try:
        bucket = s3.Bucket(S3_BUCKET)
        bucket.object_versions.delete()
        bucket.delete()
        console.print("  [green]✔[/] Deleted")
    except Exception as e:
        console.print(f"  [yellow]⚠ {e}[/]")

    # RDS (skip final snapshot for dev resource)
    console.print("[bold]RDS instance[/]")
    rds = boto3.client("rds", region_name=REGION)
    _safe(
        rds.delete_db_instance,
        DBInstanceIdentifier=RDS_INSTANCE_ID,
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )

    # IAM role
    console.print("[bold]IAM role[/]")
    iam = boto3.client("iam", region_name=REGION)
    try:
        iam.delete_role_policy(RoleName=IAM_ROLE_NAME, PolicyName="sovereign-sre-inline")
    except Exception:
        pass
    try:
        iam.detach_role_policy(
            RoleName=IAM_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
    except Exception:
        pass
    _safe(iam.delete_role, RoleName=IAM_ROLE_NAME)

    console.print()
    console.print("[bold green]Teardown complete.[/]")


if __name__ == "__main__":
    teardown()
