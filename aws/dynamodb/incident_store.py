"""
DynamoDB Incident Store
========================
Persists incident history and agent state.

Table: sovereign-sre-incidents
  PK:  incident_id (String)
  SK:  timestamp   (String, ISO8601)
  TTL: expires_at  (auto-delete after 90 days)
  GSI: status-index on (status, timestamp)

# COST SAFE: DynamoDB pay-per-request, <1000 ops/day = $0
"""


from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key, Attr

from aws.config import DYNAMODB_TABLE, REGION, DYNAMODB_TTL_DAYS


class IncidentStore:
    def __init__(self, table_name: str = DYNAMODB_TABLE, region: str = REGION):
        self._table_name = table_name
        self._region = region
        self._table: Optional[object] = None

    def _get_table(self):
        if self._table is None:
            ddb = boto3.resource("dynamodb", region_name=self._region)
            self._table = ddb.Table(self._table_name)
        return self._table

    def _ttl(self) -> int:
        return int((datetime.now(timezone.utc) + timedelta(days=DYNAMODB_TTL_DAYS)).timestamp())

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------

    def save_incident(self, incident: dict) -> str:
        incident_id = incident.get("incident_id") or str(uuid.uuid4())
        timestamp = incident.get("timestamp") or datetime.utcnow().isoformat()

        item = {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "status": incident.get("status", "running"),
            "trigger_source": incident.get("trigger_source", "manual"),
            "alarm_name": incident.get("alarm_name", ""),
            "root_cause": incident.get("root_cause", ""),
            "confidence": str(incident.get("confidence", 0)),
            "proposed_fix_summary": incident.get("proposed_fix_summary", ""),
            "diff_s3_key": incident.get("diff_s3_key", ""),
            "approval_status": incident.get("approval_status", "pending"),
            "resolution_time_ms": str(incident.get("resolution_time_ms", 0)),
            "bedrock_model_used": incident.get("bedrock_model_used", ""),
            "tokens_used": str(incident.get("tokens_used", 0)),
            "cost_usd": str(incident.get("cost_usd", 0.0)),
            "step_function_execution_arn": incident.get("step_function_execution_arn", ""),
            "expires_at": self._ttl(),
        }

        self._get_table().put_item(Item=item)
        return incident_id

    def update_incident(self, incident_id: str, timestamp: str, **updates) -> None:
        if not updates:
            return
        expr_parts, attr_names, attr_vals = [], {}, {}

        for i, (k, v) in enumerate(updates.items()):
            placeholder = f"#f{i}"
            val_key = f":v{i}"
            attr_names[placeholder] = k
            attr_vals[val_key] = str(v) if not isinstance(v, (dict, list, bool)) else v
            expr_parts.append(f"{placeholder} = {val_key}")

        self._get_table().update_item(
            Key={"incident_id": incident_id, "timestamp": timestamp},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_vals,
        )

    def get_incident(self, incident_id: str) -> Optional[dict]:
        resp = self._get_table().query(
            KeyConditionExpression=Key("incident_id").eq(incident_id),
            Limit=1,
            ScanIndexForward=False,
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    def list_incidents(self, limit: int = 20, status: Optional[str] = None) -> list[dict]:
        if status:
            resp = self._get_table().query(
                IndexName="status-index",
                KeyConditionExpression=Key("status").eq(status),
                Limit=limit,
                ScanIndexForward=False,
            )
        else:
            resp = self._get_table().scan(Limit=limit)
        return resp.get("Items", [])

    # ------------------------------------------------------------------
    # Agent state (keyed by run_id, separate from incident records)
    # ------------------------------------------------------------------

    def save_agent_state(self, run_id: str, state: dict) -> None:
        self._get_table().put_item(Item={
            "incident_id": f"agent_state#{run_id}",
            "timestamp": datetime.utcnow().isoformat(),
            "state_json": json.dumps(state, default=str),
            "expires_at": self._ttl(),
        })

    def get_agent_state(self, run_id: str) -> Optional[dict]:
        item = self.get_incident(f"agent_state#{run_id}")
        if item and "state_json" in item:
            return json.loads(item["state_json"])
        return None
