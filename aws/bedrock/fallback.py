"""
Bedrock LLM with Groq Fallback
================================
Tries BedrockLLM first; falls back to the existing Groq provider if:
  (a) AWS credentials not configured
  (b) Bedrock throttling / service error
  (c) BEDROCK_ENABLED=false in env

Presents the same complete() / stream() / chat() interface.
"""


from __future__ import annotations
import os
from typing import Iterator, Optional

from rich.console import Console

from aws.config import BEDROCK_ENABLED, BEDROCK_FALLBACK_TO_GROQ, BEDROCK_DEFAULT_MODEL

console = Console(stderr=True)


class BedrockLLMWithFallback:
    """
    Transparent wrapper: Bedrock first, Groq second.
    Drop-in replacement for GroqClient / ClaudeClient.
    """

    def __init__(self, model_name: str = BEDROCK_DEFAULT_MODEL):
        self._model_name = model_name
        self._bedrock: Optional[object] = None
        self._groq: Optional[object] = None
        self._using_bedrock: Optional[bool] = None

    def _try_bedrock(self):
        if not BEDROCK_ENABLED:
            return None
        try:
            from aws.bedrock.client import BedrockLLM
            client = BedrockLLM(model_name=self._model_name)
            # Quick probe — will raise if credentials missing
            client._bedrock()
            return client
        except Exception:
            return None

    def _get_groq(self):
        from backend.llm.groq_client import GroqClient
        return GroqClient()

    def _get_client(self):
        if self._using_bedrock is None:
            # Re-read env at call time so tests that set BEDROCK_ENABLED=false work correctly
            import os as _os
            bedrock_enabled = _os.environ.get("BEDROCK_ENABLED", "true").lower() == "true"
            fallback_enabled = _os.environ.get("BEDROCK_FALLBACK_TO_OLLAMA", "true").lower() == "true"

            bedrock = self._try_bedrock() if bedrock_enabled else None
            if bedrock:
                self._bedrock = bedrock
                self._using_bedrock = True
                console.print("[dim cyan]LLM backend: Amazon Bedrock[/]")
            elif fallback_enabled:
                self._groq = self._get_groq()
                self._using_bedrock = False
                console.print("[dim yellow]LLM backend: Groq (Bedrock unavailable)[/]")
            else:
                raise RuntimeError(
                    "Bedrock unavailable and BEDROCK_FALLBACK_TO_OLLAMA=false"
                )
        return self._bedrock if self._using_bedrock else self._groq

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        client = self._get_client()
        try:
            return client.complete(prompt, system) if self._using_bedrock else client.complete(prompt)
        except Exception as e:
            if self._using_bedrock and BEDROCK_FALLBACK_TO_GROQ:
                console.print(f"[yellow]Bedrock error, falling back to Groq: {e}[/]")
                self._using_bedrock = False
                self._groq = self._get_groq()
                return self._groq.complete(prompt)
            raise

    def stream(self, prompt: str, system: Optional[str] = None) -> Iterator[str]:
        client = self._get_client()
        if self._using_bedrock:
            yield from client.stream(prompt, system)
        else:
            # Groq client returns full string — wrap as single chunk
            yield client.complete(prompt)

    def chat(self, messages: list[dict]) -> str:
        client = self._get_client()
        if self._using_bedrock:
            return client.chat(messages)
        # Groq fallback: collapse to single prompt
        text = "\n".join(f"[{m['role']}] {m['content']}" for m in messages)
        return client.complete(text)

    @property
    def is_using_bedrock(self) -> bool:
        self._get_client()
        return bool(self._using_bedrock)
