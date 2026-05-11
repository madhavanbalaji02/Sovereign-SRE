"""
Claude Client - Anthropic SDK wrapper
"""

import os
from anthropic import Anthropic


class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    def chat(self, messages: list, tools: list = None, stream: bool = False):
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if stream:
            kwargs["stream"] = True
        return self.client.messages.create(**kwargs)

    def stream_chat(self, messages: list):
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4096,
            messages=messages,
        ) as stream:
            yield from stream.text_stream
