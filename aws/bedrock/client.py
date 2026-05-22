"""
Bedrock LLM Client
==================
Wraps boto3 bedrock-runtime Converse API.
Implements the same interface as the existing Groq/Claude clients
so backend/agents/ code needs zero changes.

# BEDROCK COST: Claude Haiku = $0.00025/1K input tokens, $0.00125/1K output
# A typical SRE pipeline run = ~5K tokens total = ~$0.008 per incident
"""

import json
from typing import Iterator, Optional

import boto3
from botocore.exceptions import ClientError

from aws.config import BEDROCK_DEFAULT_MODEL, REGION
from aws.bedrock.model_registry import get_model


class BedrockLLM:
    """Bedrock Converse API wrapper — same interface as GroqClient."""

    def __init__(
        self,
        model_name: str = BEDROCK_DEFAULT_MODEL,
        region: str = REGION,
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        self._model_id = get_model(model_name)
        self._region = region
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client: Optional[object] = None
        self._last_usage: dict = {}

    def _bedrock(self):
        if self._client is None:
            self._client = boto3.client("bedrock-runtime", region_name=self._region)
        return self._client

    def _build_messages(self, prompt: str, system: Optional[str]) -> tuple[list, list]:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system_list = [{"text": system}] if system else []
        return messages, system_list

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        """Non-streaming completion. Returns the full response text."""
        messages, system_list = self._build_messages(prompt, system)

        kwargs = dict(
            modelId=self._model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": self._max_tokens,
                "temperature": self._temperature,
            },
        )
        if system_list:
            kwargs["system"] = system_list

        resp = self._bedrock().converse(**kwargs)
        self._last_usage = resp.get("usage", {})
        return resp["output"]["message"]["content"][0]["text"]

    def stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        """Streaming completion. Yields text chunks."""
        messages, system_list = self._build_messages(prompt, system)

        kwargs = dict(
            modelId=self._model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": self._max_tokens,
                "temperature": self._temperature,
            },
        )
        if system_list:
            kwargs["system"] = system_list

        resp = self._bedrock().converse_stream(**kwargs)
        for event in resp.get("stream", []):
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                text = delta.get("text", "")
                if text:
                    yield text

    @property
    def last_usage(self) -> dict:
        """Token usage from the last complete() call."""
        return self._last_usage

    def chat(self, messages: list[dict]) -> str:
        """OpenAI-compatible chat interface (list of {role, content} dicts)."""
        # Separate system messages
        system_text = ""
        bedrock_messages = []
        for m in messages:
            if m["role"] == "system":
                system_text += m["content"] + "\n"
            else:
                bedrock_messages.append({
                    "role": m["role"],
                    "content": [{"text": m["content"]}],
                })

        kwargs = dict(
            modelId=self._model_id,
            messages=bedrock_messages,
            inferenceConfig={
                "maxTokens": self._max_tokens,
                "temperature": self._temperature,
            },
        )
        if system_text.strip():
            kwargs["system"] = [{"text": system_text.strip()}]

        resp = self._bedrock().converse(**kwargs)
        self._last_usage = resp.get("usage", {})
        return resp["output"]["message"]["content"][0]["text"]
