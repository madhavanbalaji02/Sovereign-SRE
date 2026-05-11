"""
Grok Client - xAI Grok via OpenAI-compatible API
"""

from openai import OpenAI
import os


class GrokClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
        )
        self.model = os.getenv("GROK_MODEL", "grok-3-mini")

    def chat(self, messages: list, tools: list = None, stream: bool = False):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,  # low temp for deterministic RCA
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
        return self.client.chat.completions.create(**kwargs)

    def stream_chat(self, messages: list):
        response = self.chat(messages, stream=True)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
