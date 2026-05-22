"""
AWS Amplify Setup for Sovereign-SRE Next.js Dashboard
=======================================================
Connects GitHub repo, deploys from main branch.

Usage:
    python3 aws/amplify/setup_amplify.py

# FREE TIER: Amplify 1000 build minutes/month, 15GB storage = $0
"""

import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from dotenv import load_dotenv; load_dotenv()

import boto3
from rich.console import Console
from rich.table import Table

console = Console()
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-2")
EC2_IP = (Path(__file__).parent.parent / "ec2" / ".ec2_ip").read_text().strip() if (Path(__file__).parent.parent / "ec2" / ".ec2_ip").exists() else os.environ.get("EC2_PUBLIC_IP", "3.149.31.90")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = "https://github.com/madhavanbalaji02/Sovereign-SRE"


def create_amplify_app():
    amplify = boto3.client("amplify", region_name=REGION)

    console.rule("[bold cyan]Creating Amplify App[/]")

    build_spec = (Path(__file__).parent.parent.parent / "amplify.yml").read_text()

    try:
        resp = amplify.create_app(
            name="sovereign-sre-dashboard",
            repository=REPO,
            platform="WEB_COMPUTE",
            oauthToken=GITHUB_TOKEN,
            buildSpec=build_spec,
            environmentVariables={
                "NEXT_PUBLIC_BACKEND_URL": f"http://{EC2_IP}",
                "NEXT_PUBLIC_APP_NAME": "Sovereign-SRE",
            },
            enableBranchAutoBuild=True,
            enableBranchAutoDeletion=False,
        )
        app = resp["app"]
        app_id = app["appId"]
        console.print(f"  [green]✔[/] App created: {app_id}")
    except amplify.exceptions.LimitExceededException:
        # App may already exist
        apps = amplify.list_apps()
        existing = next((a for a in apps["apps"] if a["name"] == "sovereign-sre-dashboard"), None)
        if existing:
            app_id = existing["appId"]
            console.print(f"  [dim]↷ App already exists: {app_id}[/]")
            # Update env vars
            amplify.update_app(
                appId=app_id,
                environmentVariables={
                    "NEXT_PUBLIC_BACKEND_URL": f"http://{EC2_IP}",
                    "NEXT_PUBLIC_APP_NAME": "Sovereign-SRE",
                },
            )
        else:
            raise

    # Connect main branch
    console.rule("[bold cyan]Connecting main branch[/]")
    try:
        amplify.create_branch(
            appId=app_id,
            branchName="main",
            stage="PRODUCTION",
            enableAutoBuild=True,
            environmentVariables={
                "NEXT_PUBLIC_BACKEND_URL": f"http://{EC2_IP}",
            },
        )
        console.print("  [green]✔[/] Branch 'main' connected")
    except amplify.exceptions.ResourceAlreadyExistsException:
        console.print("  [dim]↷ Branch already exists[/]")
        amplify.update_branch(
            appId=app_id,
            branchName="main",
            environmentVariables={"NEXT_PUBLIC_BACKEND_URL": f"http://{EC2_IP}"},
        )

    # Trigger build
    console.rule("[bold cyan]Starting deployment[/]")
    job = amplify.start_job(appId=app_id, branchName="main", jobType="RELEASE")
    job_id = job["jobSummary"]["jobId"]
    console.print(f"  [green]✔[/] Build started: job {job_id}")

    dashboard_url = f"https://main.{app_id}.amplifyapp.com"

    table = Table(title="\n[bold cyan]Amplify Summary[/]")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("App ID", app_id)
    table.add_row("Dashboard URL", dashboard_url)
    table.add_row("Build job", job_id)
    table.add_row("EC2 Backend", f"http://{EC2_IP}")
    table.add_row("Build console", f"https://{REGION}.console.aws.amazon.com/amplify/home#{app_id}/main")
    console.print(table)

    console.print("\n[yellow]⏳ Build takes ~5 min. Dashboard URL:[/]")
    console.print(f"  [bold cyan]{dashboard_url}[/]")
    console.print("\n[bold]Next:[/] Update CORS in backend/api/main.py with this URL, then redeploy.")

    # Save app_id and URL for other scripts
    (Path(__file__).parent / ".amplify_app_id").write_text(app_id)
    (Path(__file__).parent / ".amplify_url").write_text(dashboard_url)

    return app_id, dashboard_url


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        console.print("[red]GITHUB_TOKEN not set in .env — required for Amplify to access the repo[/]")
        sys.exit(1)
    create_amplify_app()
