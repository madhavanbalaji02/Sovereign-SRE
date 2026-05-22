"""
Deploy FastAPI backend update to EC2 via SSM Run Command (no SSH needed).
Usage: python3 aws/ec2/deploy_backend.py
"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
import boto3
from rich.console import Console

console = Console()
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")


def get_instance_id() -> str:
    ec2 = boto3.client("ec2", region_name=REGION)
    r = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": ["sovereign-sre-backend"]},
        {"Name": "instance-state-name", "Values": ["running"]},
    ])
    for res in r["Reservations"]:
        for inst in res["Instances"]:
            return inst["InstanceId"]
    raise RuntimeError("No running sovereign-sre-backend instance found")


def deploy():
    ssm = boto3.client("ssm", region_name=REGION)
    instance_id = get_instance_id()
    console.print(f"[cyan]Deploying to[/] {instance_id}...")

    commands = [
        "cd /opt/sovereign-sre",
        "git pull origin main",
        "systemctl restart sovereign-sre",
        "sleep 5",
        "systemctl is-active sovereign-sre && echo 'Service: ACTIVE' || echo 'Service: FAILED'",
        "curl -s http://localhost:8000/health || echo 'Health check failed'",
        "journalctl -u sovereign-sre -n 20 --no-pager",
    ]

    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands},
        TimeoutSeconds=120,
    )
    command_id = resp["Command"]["CommandId"]
    console.print(f"Command ID: {command_id}")

    # Poll for result
    for _ in range(24):
        time.sleep(5)
        try:
            r = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
            status = r["Status"]
            if status in ("Success", "Failed", "TimedOut", "Cancelled"):
                console.print(f"\nStatus: [{'green' if status == 'Success' else 'red'}]{status}[/]")
                console.print("\n[bold]Output:[/]")
                console.print(r.get("StandardOutputContent", ""))
                if r.get("StandardErrorContent"):
                    console.print("[red]Errors:[/]")
                    console.print(r["StandardErrorContent"])
                return status == "Success"
        except ssm.exceptions.InvocationDoesNotExist:
            pass
        console.print(".", end="")

    console.print("\n[yellow]Timed out waiting for deploy result[/]")
    return False


if __name__ == "__main__":
    deploy()
