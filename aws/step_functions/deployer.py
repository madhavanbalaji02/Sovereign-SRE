"""
Step Functions Deployer
========================
Creates or updates the Sovereign-SRE state machine from definition.json.
Replaces placeholder ARNs with real values before deploying.

# STEP FUNCTIONS COST: 4,000 state transitions FREE per month
# Each pipeline run = ~8 transitions. 4000/8 = 500 free runs/month
"""

import json
import os
from pathlib import Path
from typing import Optional

import boto3

from aws.config import STATE_MACHINE_NAME, REGION

_DEFINITION_PATH = Path(__file__).parent / "definition.json"


class StateMachineDeployer:
    def __init__(self, region: str = REGION, role_arn: str = ""):
        self._region = region
        self._role_arn = role_arn
        self._client: Optional[object] = None

    def _sf(self):
        if self._client is None:
            self._client = boto3.client("stepfunctions", region_name=self._region)
        return self._client

    def _load_definition(self, replacements: dict[str, str]) -> str:
        """Load and patch definition.json with real ARNs."""
        raw = _DEFINITION_PATH.read_text()
        for placeholder, real_value in replacements.items():
            raw = raw.replace(placeholder, real_value)
        return raw

    def deploy(self, role_arn: str, replacements: Optional[dict[str, str]] = None) -> str:
        """Create or update the state machine. Returns its ARN."""
        definition = self._load_definition(replacements or {})
        json.loads(definition)  # validate JSON before sending

        # Check if it already exists
        existing_arn = self.get_arn()

        if existing_arn:
            self._sf().update_state_machine(
                stateMachineArn=existing_arn,
                definition=definition,
                roleArn=role_arn,
            )
            return existing_arn
        else:
            resp = self._sf().create_state_machine(
                name=STATE_MACHINE_NAME,
                definition=definition,
                roleArn=role_arn,
                type="STANDARD",
                loggingConfiguration={"level": "ERROR", "includeExecutionData": False},
            )
            return resp["stateMachineArn"]

    def get_arn(self) -> Optional[str]:
        try:
            paginator = self._sf().get_paginator("list_state_machines")
            for page in paginator.paginate():
                for sm in page["stateMachines"]:
                    if sm["name"] == STATE_MACHINE_NAME:
                        return sm["stateMachineArn"]
        except Exception:
            pass
        return None

    def delete(self) -> None:
        arn = self.get_arn()
        if arn:
            self._sf().delete_state_machine(stateMachineArn=arn)
