"""
AWS Setup — master idempotent resource creation script
========================================================
Creates all Sovereign-SRE AWS resources in the correct order.

Usage:
    python aws/setup.py

All steps are idempotent — safe to re-run. Creates resources only if they
don't already exist, and updates them when possible.

Resource creation order (matches dependency graph):
 1. IAM role + inline policies
 2. S3 bucket + lifecycle + versioning
 3. DynamoDB table + GSI + TTL
 4. SNS topic + email subscription
 5. SSM parameters (reads from .env)
 6. CloudWatch log group + alarms
 7. Kinesis Firehose delivery stream → S3
 8. RDS db.t3.micro + schema.sql
 9. EventBridge rule
10. Lambda function (zip + upload)
11. Step Functions state machine
12. EventBridge target → Lambda
"""

import io
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Resolve account ID at runtime
_sts = boto3.client("sts", region_name=REGION)
ACCOUNT_ID = _sts.get_caller_identity()["Account"]

# Resource names (must match aws/config.py)
IAM_ROLE_NAME = "sovereign-sre-execution-role"
S3_BUCKET = f"sovereign-sre-artifacts-{ACCOUNT_ID}"
DYNAMODB_TABLE = "sovereign-sre-incidents"
SNS_TOPIC_NAME = "sovereign-sre-approvals"
CW_LOG_GROUP = "/sovereign-sre/incidents"
FIREHOSE_STREAM = "sovereign-sre-logs"
LAMBDA_NAME = "sovereign-sre-remediation-trigger"
STATE_MACHINE_NAME = "sovereign-sre-pipeline"
EVENTBRIDGE_RULE = "sovereign-sre-alarm-trigger"
RDS_INSTANCE_ID = "sovereign-sre-db"
RDS_DB_NAME = "sovereignsre"
RDS_USER = "sreadmin"

results: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(msg: str) -> None:
    console.print(f"  [green]✔[/] {msg}")


def _skip(msg: str) -> None:
    console.print(f"  [dim]↷ {msg} (already exists)[/]")


def _section(title: str) -> None:
    console.rule(f"[bold cyan]{title}[/]")


# ---------------------------------------------------------------------------
# Step 1: IAM Role
# ---------------------------------------------------------------------------


def create_iam_role():
    _section("1. IAM Role")
    iam = boto3.client("iam", region_name=REGION)

    trust = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": ["lambda.amazonaws.com", "states.amazonaws.com"]
                },
                "Action": "sts:AssumeRole",
            }
        ],
    })

    try:
        resp = iam.create_role(
            RoleName=IAM_ROLE_NAME,
            AssumeRolePolicyDocument=trust,
            Description="Sovereign-SRE least-privilege execution role",
        )
        role_arn = resp["Role"]["Arn"]
        _ok(f"Created role: {role_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=IAM_ROLE_NAME)["Role"]["Arn"]
        _skip(f"Role ARN: {role_arn}")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
             "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
                                            "dynamodb:Query", "dynamodb:Scan"],
             "Resource": f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/{DYNAMODB_TABLE}*"},
            {"Effect": "Allow", "Action": ["cloudwatch:PutMetricData", "cloudwatch:GetMetricStatistics",
                                            "cloudwatch:DescribeAlarms"],
             "Resource": "*"},
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream",
                                            "logs:PutLogEvents", "logs:FilterLogEvents",
                                            "logs:DescribeLogStreams"],
             "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:/sovereign-sre*:*"},
            {"Effect": "Allow", "Action": ["sns:Publish"],
             "Resource": f"arn:aws:sns:{REGION}:{ACCOUNT_ID}:sovereign-sre*"},
            {"Effect": "Allow", "Action": ["ssm:GetParameter", "ssm:GetParameters"],
             "Resource": f"arn:aws:ssm:{REGION}:{ACCOUNT_ID}:parameter/sovereign-sre/*"},
            {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
             "Resource": "*"},
            {"Effect": "Allow", "Action": ["lambda:InvokeFunction"],
             "Resource": f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:sovereign-sre*"},
            {"Effect": "Allow", "Action": ["states:StartExecution", "states:DescribeExecution",
                                            "states:SendTaskSuccess", "states:SendTaskFailure"],
             "Resource": "*"},
            {"Effect": "Allow", "Action": ["firehose:PutRecord", "firehose:PutRecordBatch"],
             "Resource": f"arn:aws:firehose:{REGION}:{ACCOUNT_ID}:deliverystream/{FIREHOSE_STREAM}"},
            {"Effect": "Allow", "Action": ["rds:DescribeDBInstances"], "Resource": "*"},
        ],
    }

    iam.put_role_policy(
        RoleName=IAM_ROLE_NAME,
        PolicyName="sovereign-sre-inline",
        PolicyDocument=json.dumps(policy),
    )
    # Attach basic Lambda execution policy
    try:
        iam.attach_role_policy(
            RoleName=IAM_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
    except Exception:
        pass

    results["IAM Role"] = role_arn
    return role_arn


# ---------------------------------------------------------------------------
# Step 2: S3 Bucket
# ---------------------------------------------------------------------------


def create_s3_bucket():
    _section("2. S3 Bucket")
    s3 = boto3.client("s3", region_name=REGION)

    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=S3_BUCKET)
        else:
            s3.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        _ok(f"Created bucket: {S3_BUCKET}")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            _skip(S3_BUCKET)
        else:
            raise

    # Lifecycle: delete objects after 30 days
    s3.put_bucket_lifecycle_configuration(
        Bucket=S3_BUCKET,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "sovereign-sre-30day-cleanup",
                    "Status": "Enabled",
                    "Expiration": {"Days": 30},
                    "Filter": {"Prefix": "incidents/"},
                }
            ]
        },
    )
    s3.put_bucket_versioning(
        Bucket=S3_BUCKET,
        VersioningConfiguration={"Status": "Enabled"},
    )

    results["S3 Bucket"] = S3_BUCKET
    return S3_BUCKET


# ---------------------------------------------------------------------------
# Step 3: DynamoDB
# ---------------------------------------------------------------------------


def create_dynamodb_table():
    _section("3. DynamoDB Table")
    ddb = boto3.client("dynamodb", region_name=REGION)

    try:
        ddb.create_table(
            TableName=DYNAMODB_TABLE,
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
        # Wait for table to be active
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName=DYNAMODB_TABLE)
        _ok(f"Created table: {DYNAMODB_TABLE}")
    except ddb.exceptions.ResourceInUseException:
        _skip(DYNAMODB_TABLE)

    # Enable TTL
    try:
        ddb.update_time_to_live(
            TableName=DYNAMODB_TABLE,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": "expires_at"},
        )
    except Exception:
        pass

    arn = f"arn:aws:dynamodb:{REGION}:{ACCOUNT_ID}:table/{DYNAMODB_TABLE}"
    results["DynamoDB Table"] = DYNAMODB_TABLE
    return DYNAMODB_TABLE


# ---------------------------------------------------------------------------
# Step 4: SNS Topic
# ---------------------------------------------------------------------------


def create_sns_topic():
    _section("4. SNS Topic")
    sns = boto3.client("sns", region_name=REGION)

    resp = sns.create_topic(Name=SNS_TOPIC_NAME)
    topic_arn = resp["TopicArn"]
    _ok(f"Topic ARN: {topic_arn}")

    approval_email = os.environ.get("SNS_APPROVAL_EMAIL", "")
    if approval_email:
        sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=approval_email)
        _ok(f"Subscribed {approval_email} (check inbox to confirm)")

    results["SNS Topic"] = topic_arn
    return topic_arn


# ---------------------------------------------------------------------------
# Step 5: SSM Parameters
# ---------------------------------------------------------------------------


def create_ssm_parameters(sns_topic_arn: str):
    _section("5. SSM Parameter Store")
    ssm = boto3.client("ssm", region_name=REGION)

    param_map = {
        "/sovereign-sre/groq-api-key":       (os.environ.get("GROQ_API_KEY", ""), "SecureString"),
        "/sovereign-sre/anthropic-api-key":  (os.environ.get("ANTHROPIC_API_KEY", ""), "SecureString"),
        "/sovereign-sre/github-token":       (os.environ.get("GITHUB_TOKEN", ""), "SecureString"),
        "/sovereign-sre/backend-url":        (os.environ.get("BACKEND_URL", "http://localhost:8001"), "String"),
        "/sovereign-sre/sns-topic-arn":      (sns_topic_arn, "String"),
    }

    for path, (value, param_type) in param_map.items():
        if not value:
            console.print(f"  [yellow]⚠ Skipping {path} (empty value)[/]")
            continue
        ssm.put_parameter(Name=path, Value=value, Type=param_type, Overwrite=True)
        _ok(f"Set {path}")


# ---------------------------------------------------------------------------
# Step 6: CloudWatch Log Group + Alarms
# ---------------------------------------------------------------------------


def create_cloudwatch_resources(sns_topic_arn: str):
    _section("6. CloudWatch Log Group + Alarms")
    logs = boto3.client("logs", region_name=REGION)

    try:
        logs.create_log_group(logGroupName=CW_LOG_GROUP)
        _ok(f"Created log group: {CW_LOG_GROUP}")
    except logs.exceptions.ResourceAlreadyExistsException:
        _skip(CW_LOG_GROUP)

    from aws.cloudwatch.alarms import AlarmManager
    alarms = AlarmManager(region=REGION, sns_topic_arn=sns_topic_arn)
    alarms.create_standard_alarms()
    _ok("Created standard alarms")


# ---------------------------------------------------------------------------
# Step 7: Kinesis Firehose
# ---------------------------------------------------------------------------


def create_firehose(role_arn: str):
    _section("7. Kinesis Firehose")
    fh = boto3.client("firehose", region_name=REGION)

    try:
        fh.create_delivery_stream(
            DeliveryStreamName=FIREHOSE_STREAM,
            DeliveryStreamType="DirectPut",
            S3DestinationConfiguration={
                "RoleARN": role_arn,
                "BucketARN": f"arn:aws:s3:::{S3_BUCKET}",
                "Prefix": "firehose-logs/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
                "ErrorOutputPrefix": "firehose-errors/",
                "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 60},
                "CloudWatchLoggingOptions": {
                    "Enabled": True,
                    "LogGroupName": "/aws/kinesisfirehose/sovereign-sre-logs",
                    "LogStreamName": "S3Delivery",
                },
            },
        )
        _ok(f"Created Firehose stream: {FIREHOSE_STREAM}")
    except fh.exceptions.ResourceInUseException:
        _skip(FIREHOSE_STREAM)

    results["Firehose Stream"] = FIREHOSE_STREAM


# ---------------------------------------------------------------------------
# Step 8: RDS Instance
# ---------------------------------------------------------------------------


def create_rds_instance():
    _section("8. RDS Instance (pgvector)")
    rds = boto3.client("rds", region_name=REGION)
    rds_password = os.environ.get("RDS_PASSWORD", "SovereignSRE2024!")

    try:
        resp = rds.create_db_instance(
            DBInstanceIdentifier=RDS_INSTANCE_ID,
            DBInstanceClass="db.t3.micro",
            Engine="postgres",
            EngineVersion="15",
            MasterUsername=RDS_USER,
            MasterUserPassword=rds_password,
            DBName=RDS_DB_NAME,
            AllocatedStorage=20,
            PubliclyAccessible=True,
            BackupRetentionPeriod=1,
            MultiAZ=False,
            Tags=[{"Key": "Project", "Value": "sovereign-sre"}],
        )
        endpoint = resp["DBInstance"].get("Endpoint", {}).get("Address", "pending")
        _ok(f"Creating RDS instance (this takes ~5 min): {RDS_INSTANCE_ID}")
        _ok(f"Endpoint (may still be pending): {endpoint}")
    except rds.exceptions.DBInstanceAlreadyExistsFault:
        resp = rds.describe_db_instances(DBInstanceIdentifier=RDS_INSTANCE_ID)
        endpoint = resp["DBInstances"][0]["Endpoint"]["Address"]
        _skip(f"RDS endpoint: {endpoint}")

    # Store connection string in SSM
    ssm = boto3.client("ssm", region_name=REGION)
    conn_str = (
        f"postgresql://{RDS_USER}:{rds_password}@"
        f"{endpoint}:{5432}/{RDS_DB_NAME}"
        if "pending" not in str(endpoint) else ""
    )
    if conn_str:
        ssm.put_parameter(
            Name="/sovereign-sre/rds-connection-string",
            Value=conn_str,
            Type="SecureString",
            Overwrite=True,
        )
        _ok("Stored connection string in SSM")

    rds_arn = f"arn:aws:rds:{REGION}:{ACCOUNT_ID}:db:{RDS_INSTANCE_ID}"
    results["RDS Instance"] = f"{RDS_INSTANCE_ID} ({endpoint})"
    return endpoint


# ---------------------------------------------------------------------------
# Step 9: EventBridge Rule (target added in step 12 after Lambda ARN is known)
# ---------------------------------------------------------------------------


def create_eventbridge_rule():
    _section("9. EventBridge Rule")
    from aws.eventbridge.rules import EventBridgeManager
    eb = EventBridgeManager(region=REGION)
    rule_arn = eb.create_alarm_trigger_rule()
    _ok(f"Rule ARN: {rule_arn}")
    results["EventBridge Rule"] = EVENTBRIDGE_RULE
    return rule_arn


# ---------------------------------------------------------------------------
# Step 10: Lambda Function
# ---------------------------------------------------------------------------


def create_lambda(role_arn: str, sns_topic_arn: str, sm_arn: str = "") -> str:
    _section("10. Lambda Function")
    lam = boto3.client("lambda", region_name=REGION)

    # Zip the handler
    handler_path = Path(__file__).parent / "lambda_functions" / "remediation_trigger.py"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(handler_path, "remediation_trigger.py")
    buf.seek(0)
    zip_bytes = buf.read()

    env_vars = {
        "STATE_MACHINE_ARN": sm_arn,
        "BACKEND_URL": os.environ.get("BACKEND_URL", "http://localhost:8001"),
        "SNS_TOPIC_ARN": sns_topic_arn,
    }

    try:
        resp = lam.create_function(
            FunctionName=LAMBDA_NAME,
            Runtime="python3.12",
            Role=role_arn,
            Handler="remediation_trigger.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30,
            MemorySize=256,
            Environment={"Variables": env_vars},
            Tags={"Project": "sovereign-sre"},
        )
        lambda_arn = resp["FunctionArn"]
        _ok(f"Created Lambda: {lambda_arn}")
    except lam.exceptions.ResourceConflictException:
        lam.update_function_code(FunctionName=LAMBDA_NAME, ZipFile=zip_bytes)
        lam.update_function_configuration(
            FunctionName=LAMBDA_NAME,
            Environment={"Variables": env_vars},
        )
        resp = lam.get_function(FunctionName=LAMBDA_NAME)
        lambda_arn = resp["Configuration"]["FunctionArn"]
        _skip(f"Updated Lambda: {lambda_arn}")

    results["Lambda"] = lambda_arn
    return lambda_arn


# ---------------------------------------------------------------------------
# Step 11: Step Functions State Machine
# ---------------------------------------------------------------------------


def create_step_functions(role_arn: str, sns_topic_arn: str) -> str:
    _section("11. Step Functions State Machine")
    from aws.step_functions.deployer import StateMachineDeployer

    deployer = StateMachineDeployer(region=REGION)
    sm_arn = deployer.deploy(role_arn=role_arn)
    _ok(f"State machine ARN: {sm_arn}")
    results["Step Functions"] = sm_arn
    return sm_arn


# ---------------------------------------------------------------------------
# Step 12: Wire EventBridge → Lambda
# ---------------------------------------------------------------------------


def wire_eventbridge_to_lambda(lambda_arn: str, rule_arn: str):
    _section("12. Wire EventBridge → Lambda")
    from aws.eventbridge.rules import EventBridgeManager
    eb = EventBridgeManager(region=REGION)
    lam = boto3.client("lambda", region_name=REGION)

    eb.add_lambda_target(lambda_arn)
    eb.grant_lambda_invoke(lam, LAMBDA_NAME, rule_arn)
    _ok("EventBridge target → Lambda wired")


# ---------------------------------------------------------------------------
# Final summary table
# ---------------------------------------------------------------------------


def print_summary():
    console.print()
    table = Table(title="[bold cyan]Sovereign-SRE AWS Resources[/]", show_header=True)
    table.add_column("Resource", style="cyan")
    table.add_column("ARN / ID", style="green")

    for resource, arn in results.items():
        table.add_row(resource, arn)

    console.print(table)
    console.print()
    console.print("[bold]Next steps:[/]")
    console.print("  1. python aws/pgvector/migrate.py     # migrate ChromaDB → pgvector")
    console.print("  2. pytest tests/ -v                   # run all tests")
    console.print()
    console.print("[dim]Cost estimate: ~$1/month (Bedrock). Everything else on free tier.[/]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    console.print("[bold cyan]🛡️  Sovereign-SRE AWS Setup[/]")
    console.print(f"Region: {REGION} | Account: {ACCOUNT_ID}")
    console.print()

    try:
        role_arn = create_iam_role()
        time.sleep(10)  # IAM propagation delay

        s3_bucket = create_s3_bucket()
        create_dynamodb_table()
        sns_topic_arn = create_sns_topic()
        create_ssm_parameters(sns_topic_arn)
        create_cloudwatch_resources(sns_topic_arn)
        create_firehose(role_arn)
        create_rds_instance()
        rule_arn = create_eventbridge_rule()

        # Lambda needs SM ARN, but SM needs Lambda ARN — create Lambda first with empty SM ARN
        lambda_arn = create_lambda(role_arn, sns_topic_arn, sm_arn="")
        sm_arn = create_step_functions(role_arn, sns_topic_arn)

        # Update Lambda with real SM ARN
        lam = boto3.client("lambda", region_name=REGION)
        lam.update_function_configuration(
            FunctionName=LAMBDA_NAME,
            Environment={"Variables": {
                "STATE_MACHINE_ARN": sm_arn,
                "BACKEND_URL": os.environ.get("BACKEND_URL", "http://localhost:8001"),
                "SNS_TOPIC_ARN": sns_topic_arn,
            }},
        )

        wire_eventbridge_to_lambda(lambda_arn, rule_arn)
        print_summary()

    except Exception as e:
        console.print(f"\n[bold red]Setup failed:[/] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
