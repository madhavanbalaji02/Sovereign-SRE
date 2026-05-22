"""
SSM Parameter Store — secrets management
=========================================
Loads API keys from SSM at startup; falls back to os.environ / .env
for local dev when AWS is not configured.
"""

import os
import time
from typing import Optional

from aws.config import SSM_PREFIX, SSM_KEYS, REGION

# In-memory cache: param_name → (value, expiry_timestamp)
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 300  # 5 minutes


class SecretsManager:
    def __init__(self, region: str = REGION):
        self._region = region
        self._client: Optional[object] = None
        self._available: Optional[bool] = None  # lazy-probe AWS once

    def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("ssm", region_name=self._region)
        return self._client

    def _is_aws_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import boto3
            sts = boto3.client("sts", region_name=self._region)
            sts.get_caller_identity()
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def get(self, key: str) -> str:
        """
        Fetch a parameter. Strips /sovereign-sre/ prefix if included.
        Falls back to os.environ when AWS is unavailable.
        """
        # Normalize key
        if key.startswith(SSM_PREFIX):
            param_path = key
        else:
            param_path = SSM_KEYS.get(key, f"{SSM_PREFIX}/{key}")

        # Check cache
        now = time.monotonic()
        if param_path in _cache:
            value, expiry = _cache[param_path]
            if now < expiry:
                return value

        if self._is_aws_available():
            try:
                resp = self._get_client().get_parameter(
                    Name=param_path,
                    WithDecryption=True,
                )
                value = resp["Parameter"]["Value"]
                _cache[param_path] = (value, now + _CACHE_TTL)
                return value
            except Exception:
                pass  # fall through to env

        # Env fallback: convert /sovereign-sre/groq-api-key → GROQ_API_KEY
        env_key = param_path.split("/")[-1].replace("-", "_").upper()
        return os.environ.get(env_key, "")

    def load_all_to_env(self) -> None:
        """Load every known SSM parameter into os.environ (called at startup)."""
        if not self._is_aws_available():
            return  # local dev — .env already loaded by python-dotenv

        env_map = {
            "groq-api-key":          "GROQ_API_KEY",
            "anthropic-api-key":     "ANTHROPIC_API_KEY",
            "github-token":          "GITHUB_TOKEN",
            "rds-connection-string": "RDS_CONNECTION_STRING",
            "backend-url":           "BACKEND_URL",
            "sns-topic-arn":         "SNS_TOPIC_ARN",
        }
        for ssm_key, env_key in env_map.items():
            value = self.get(ssm_key)
            if value:
                os.environ.setdefault(env_key, value)

    def put(self, key: str, value: str, secure: bool = True) -> None:
        """Write (or overwrite) a parameter."""
        if key.startswith(SSM_PREFIX):
            param_path = key
        else:
            param_path = SSM_KEYS.get(key, f"{SSM_PREFIX}/{key}")

        param_type = "SecureString" if secure else "String"
        self._get_client().put_parameter(
            Name=param_path,
            Value=value,
            Type=param_type,
            Overwrite=True,
        )
        _cache.pop(param_path, None)
