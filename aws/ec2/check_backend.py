"""
Check EC2 backend health via SSM Run Command.
Usage: python3 aws/ec2/check_backend.py
"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()
import boto3, requests
from rich.console import Console
from rich.table import Table

console = Console()
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")


def check():
    ec2 = boto3.client("ec2", region_name=REGION)
    ssm = boto3.client("ssm", region_name=REGION)

    r = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": ["sovereign-sre-backend"]},
        {"Name": "instance-state-name", "Values": ["running", "stopped", "pending"]},
    ])

    table = Table(title="[bold cyan]EC2 Backend Status[/]")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")

    for res in r["Reservations"]:
        for inst in res["Instances"]:
            iid = inst["InstanceId"]
            state = inst["State"]["Name"]
            pub_ip = inst.get("PublicIpAddress", "none")
            table.add_row("Instance ID", iid)
            table.add_row("State", state)
            table.add_row("Public IP", pub_ip)

            # HTTP health check
            if pub_ip and pub_ip != "none":
                try:
                    resp = requests.get(f"http://{pub_ip}/health", timeout=5)
                    table.add_row("HTTP /health", f"[green]{resp.status_code} {resp.json().get('status','?')}[/]")
                except Exception as e:
                    table.add_row("HTTP /health", f"[red]FAILED: {e}[/]")

            # SSM logs (last 30 lines)
            if state == "running":
                try:
                    cmd = ssm.send_command(
                        InstanceIds=[iid],
                        DocumentName="AWS-RunShellScript",
                        Parameters={"commands": [
                            "systemctl is-active sovereign-sre",
                            "journalctl -u sovereign-sre -n 30 --no-pager",
                        ]},
                        TimeoutSeconds=30,
                    )
                    cid = cmd["Command"]["CommandId"]
                    for _ in range(12):
                        time.sleep(3)
                        try:
                            inv = ssm.get_command_invocation(CommandId=cid, InstanceId=iid)
                            if inv["Status"] in ("Success", "Failed"):
                                table.add_row("Service status", inv.get("StandardOutputContent","").split("\n")[0])
                                break
                        except Exception:
                            pass
                except Exception as e:
                    table.add_row("SSM logs", f"[yellow]{e}[/]")

    console.print(table)


if __name__ == "__main__":
    check()
