"""
EC2 t2.micro Setup for Sovereign-SRE FastAPI Backend
======================================================
Creates security group, key pair, launches instance, allocates Elastic IP.

Usage:
    python3 aws/ec2/setup_ec2.py

# FREE TIER: t2.micro = 750 hrs/month free for 12 months = $0
# FREE TIER: Elastic IP free while instance is running
# WATCH: Elastic IP costs $0.005/hr if instance is STOPPED — always TERMINATE, never stop
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import boto3
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
KEY_NAME = "sovereign-sre-key"
KEY_PATH = Path.home() / ".ssh" / "sovereign-sre-key.pem"
SG_NAME = "sovereign-sre-backend-sg"
INSTANCE_NAME = "sovereign-sre-backend"
AMI_ID = "ami-0942f61c0243edad7"   # Amazon Linux 2, us-east-2 (latest)
INSTANCE_TYPE = "t3.micro"          # FREE TIER (750 hrs/month, us-east-2)

ec2 = boto3.client("ec2", region_name=REGION)
ec2r = boto3.resource("ec2", region_name=REGION)


def get_my_ip() -> str:
    try:
        return requests.get("https://ipv4.icanhazip.com", timeout=5).text.strip()
    except Exception:
        return requests.get("https://ifconfig.me", timeout=5).text.strip()


# ---------------------------------------------------------------------------
# Step 1: Security Group
# ---------------------------------------------------------------------------
def create_security_group(my_ip: str) -> str:
    console.rule("[bold cyan]1. Security Group[/]")
    try:
        resp = ec2.create_security_group(
            GroupName=SG_NAME,
            Description="Sovereign-SRE FastAPI backend security group",
        )
        sg_id = resp["GroupId"]
        console.print(f"  [green]✔[/] Created: {sg_id}")
    except ClientError as e:
        if "already exists" in str(e):
            r = ec2.describe_security_groups(GroupNames=[SG_NAME])
            sg_id = r["SecurityGroups"][0]["GroupId"]
            console.print(f"  [dim]↷ Already exists: {sg_id}[/]")
        else:
            raise

    # Add inbound rules (idempotent — ignore duplicate errors)
    rules = [
        {"IpProtocol": "tcp", "FromPort": 22,   "ToPort": 22,   "IpRanges": [{"CidrIp": f"{my_ip}/32",  "Description": "SSH from dev machine"}]},
        {"IpProtocol": "tcp", "FromPort": 80,   "ToPort": 80,   "IpRanges": [{"CidrIp": "0.0.0.0/0",   "Description": "HTTP public"}]},
        {"IpProtocol": "tcp", "FromPort": 443,  "ToPort": 443,  "IpRanges": [{"CidrIp": "0.0.0.0/0",   "Description": "HTTPS public"}]},
        {"IpProtocol": "tcp", "FromPort": 8000, "ToPort": 8000, "IpRanges": [{"CidrIp": "0.0.0.0/0",   "Description": "FastAPI direct (remove after nginx)"}]},
    ]
    try:
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=rules)
        console.print("  [green]✔[/] Inbound rules added")
    except ClientError as e:
        if "already exists" in str(e) or "Duplicate" in str(e):
            console.print("  [dim]↷ Rules already set[/]")
        else:
            console.print(f"  [yellow]⚠ Rules: {e}[/]")

    # Egress all
    try:
        ec2.authorize_security_group_egress(
            GroupId=sg_id,
            IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
        )
    except ClientError:
        pass

    return sg_id


# ---------------------------------------------------------------------------
# Step 2: Key Pair
# ---------------------------------------------------------------------------
def create_key_pair() -> None:
    console.rule("[bold cyan]2. Key Pair[/]")
    if KEY_PATH.exists():
        console.print(f"  [dim]↷ Key already exists: {KEY_PATH}[/]")
        return

    try:
        resp = ec2.create_key_pair(KeyName=KEY_NAME, KeyType="rsa")
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEY_PATH.write_text(resp["KeyMaterial"])
        KEY_PATH.chmod(0o400)
        console.print(f"  [green]✔[/] Key saved: {KEY_PATH}")
    except ClientError as e:
        if "already exists" in str(e):
            console.print(f"  [yellow]⚠ Key pair exists in AWS but {KEY_PATH} is missing.[/]")
            console.print("    Delete the key pair in EC2 console and re-run, or copy the .pem manually.")
        else:
            raise


# ---------------------------------------------------------------------------
# Step 3: Launch EC2 Instance
# ---------------------------------------------------------------------------
def launch_instance(sg_id: str) -> str:
    console.rule("[bold cyan]3. EC2 Instance[/]")

    # Check if already running
    r = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [INSTANCE_NAME]},
        {"Name": "instance-state-name", "Values": ["running", "pending", "stopped"]},
    ])
    for res in r["Reservations"]:
        for inst in res["Instances"]:
            iid = inst["InstanceId"]
            state = inst["State"]["Name"]
            console.print(f"  [dim]↷ Instance already exists: {iid} ({state})[/]")
            return iid

    bootstrap = (Path(__file__).parent / "bootstrap.sh").read_text()

    resp = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        UserData=bootstrap,
        IamInstanceProfile={"Name": "sovereign-sre-ec2-profile"},
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name",    "Value": INSTANCE_NAME},
                {"Key": "Project", "Value": "sovereign-sre"},
            ],
        }],
    )
    instance_id = resp["Instances"][0]["InstanceId"]
    console.print(f"  [green]✔[/] Launched: {instance_id}")

    console.print("  Waiting for instance to be running...")
    waiter = ec2.get_waiter("instance_running")
    waiter.wait(InstanceIds=[instance_id])
    console.print("  [green]✔[/] Instance running")
    return instance_id


# ---------------------------------------------------------------------------
# Step 4: IAM Instance Profile (for SSM access)
# ---------------------------------------------------------------------------
def create_instance_profile() -> None:
    console.rule("[bold cyan]4. IAM Instance Profile[/]")
    iam = boto3.client("iam", region_name=REGION)
    profile_name = "sovereign-sre-ec2-profile"
    role_name = "sovereign-sre-ec2-role"

    # Role
    import json
    trust = json.dumps({"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole",
    }]})
    try:
        iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust)
        console.print(f"  [green]✔[/] IAM role created: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        console.print(f"  [dim]↷ Role exists: {role_name}[/]")

    for policy in [
        "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
        "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess",
    ]:
        try:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy)
        except Exception:
            pass

    # Inline policy for SSM parameter access + Bedrock + DynamoDB + S3
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    inline = json.dumps({"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
         "Resource": f"arn:aws:ssm:{REGION}:{account_id}:parameter/sovereign-sre/*"},
        {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": "*"},
        {"Effect": "Allow", "Action": ["dynamodb:*"], "Resource": f"arn:aws:dynamodb:{REGION}:{account_id}:table/sovereign-sre-*"},
        {"Effect": "Allow", "Action": ["s3:*"], "Resource": [f"arn:aws:s3:::sovereign-sre-artifacts-{account_id}", f"arn:aws:s3:::sovereign-sre-artifacts-{account_id}/*"]},
        {"Effect": "Allow", "Action": ["states:*"], "Resource": f"arn:aws:states:{REGION}:{account_id}:stateMachine:sovereign-sre-*"},
        {"Effect": "Allow", "Action": ["sns:Publish"], "Resource": f"arn:aws:sns:{REGION}:{account_id}:sovereign-sre-*"},
        {"Effect": "Allow", "Action": ["cloudwatch:PutMetricData"], "Resource": "*"},
        {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
    ]})
    iam.put_role_policy(RoleName=role_name, PolicyName="sovereign-sre-ec2-inline", PolicyDocument=inline)

    # Instance profile
    try:
        iam.create_instance_profile(InstanceProfileName=profile_name)
        iam.add_role_to_instance_profile(InstanceProfileName=profile_name, RoleName=role_name)
        console.print(f"  [green]✔[/] Instance profile created: {profile_name}")
        time.sleep(10)  # IAM propagation
    except iam.exceptions.EntityAlreadyExistsException:
        console.print(f"  [dim]↷ Instance profile exists: {profile_name}[/]")


# ---------------------------------------------------------------------------
# Step 5: Elastic IP
# ---------------------------------------------------------------------------
def allocate_elastic_ip(instance_id: str) -> str:
    console.rule("[bold cyan]5. Elastic IP[/]")

    # Check if one is already associated
    r = ec2.describe_addresses(Filters=[{"Name": "instance-id", "Values": [instance_id]}])
    if r["Addresses"]:
        ip = r["Addresses"][0]["PublicIp"]
        console.print(f"  [dim]↷ Already associated: {ip}[/]")
        return ip

    alloc = ec2.allocate_address(Domain="vpc")
    alloc_id = alloc["AllocationId"]
    public_ip = alloc["PublicIp"]

    ec2.associate_address(InstanceId=instance_id, AllocationId=alloc_id)
    console.print(f"  [green]✔[/] Elastic IP: {public_ip}")
    return public_ip


# ---------------------------------------------------------------------------
# Step 6: Allow EC2 → RDS (port 5432)
# ---------------------------------------------------------------------------
def allow_ec2_to_rds(sg_id: str) -> None:
    console.rule("[bold cyan]6. EC2 → RDS Access[/]")
    rds_sg_id = "sg-03a065fe7a145639c"  # RDS security group from earlier setup
    try:
        ec2.authorize_security_group_ingress(
            GroupId=rds_sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "UserIdGroupPairs": [{"GroupId": sg_id, "Description": "EC2 backend → RDS"}],
            }],
        )
        console.print("  [green]✔[/] EC2 SG allowed to reach RDS on 5432")
    except ClientError as e:
        if "already exists" in str(e) or "Duplicate" in str(e):
            console.print("  [dim]↷ Rule already exists[/]")
        else:
            console.print(f"  [yellow]⚠ {e}[/]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    console.print("[bold cyan]🛡️  Sovereign-SRE EC2 Setup[/]")
    console.print(f"Region: {REGION} | AMI: {AMI_ID} | Type: {INSTANCE_TYPE}\n")

    my_ip = get_my_ip()
    console.print(f"Your IP: {my_ip}\n")

    create_instance_profile()
    sg_id = create_security_group(my_ip)
    create_key_pair()
    instance_id = launch_instance(sg_id)
    public_ip = allocate_elastic_ip(instance_id)
    allow_ec2_to_rds(sg_id)

    # Update SSM with EC2 backend URL
    console.rule("[bold cyan]7. Update SSM[/]")
    ssm = boto3.client("ssm", region_name=REGION)
    backend_url = f"http://{public_ip}"
    ssm.put_parameter(Name="/sovereign-sre/backend-url", Value=backend_url, Type="String", Overwrite=True)
    console.print(f"  [green]✔[/] SSM /sovereign-sre/backend-url = {backend_url}")

    # Update Lambda env
    try:
        sf = boto3.client("stepfunctions", region_name=REGION)
        sms = sf.list_state_machines()
        sm_arn = next((s["stateMachineArn"] for s in sms["stateMachines"] if "sovereign-sre" in s["name"]), "")

        lam = boto3.client("lambda", region_name=REGION)
        lam.update_function_configuration(
            FunctionName="sovereign-sre-remediation-trigger",
            Environment={"Variables": {
                "BACKEND_URL": backend_url,
                "STATE_MACHINE_ARN": sm_arn,
                "SNS_TOPIC_ARN": os.environ.get("SNS_TOPIC_ARN", ""),
            }},
        )
        console.print("  [green]✔[/] Lambda BACKEND_URL updated")
    except Exception as e:
        console.print(f"  [yellow]⚠ Lambda update: {e}[/]")

    # Print summary
    table = Table(title="\n[bold cyan]EC2 Summary[/]")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Instance ID", instance_id)
    table.add_row("Public IP (Elastic)", public_ip)
    table.add_row("Backend URL", backend_url)
    table.add_row("Health Check", f"curl {backend_url}/health")
    table.add_row("SSH", f"ssh -i ~/.ssh/sovereign-sre-key.pem ec2-user@{public_ip}")
    table.add_row("Bootstrap log", f"ssh ... 'sudo tail -f /var/log/cloud-init-output.log'")
    console.print(table)
    console.print("\n[yellow]⏳ Bootstrap takes ~5 min. Monitor with:[/]")
    console.print(f"  ssh -i ~/.ssh/sovereign-sre-key.pem ec2-user@{public_ip} 'sudo journalctl -u sovereign-sre -f'")

    # Save public IP to file for other scripts
    (Path(__file__).parent / ".ec2_ip").write_text(public_ip)
    console.print(f"\n[dim]IP saved to aws/ec2/.ec2_ip for use by other scripts[/]")
