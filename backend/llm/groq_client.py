"""
Groq Client - Llama 3.3 on Groq LPU hardware
"""

import os
import time
from groq import Groq, RateLimitError


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    def chat(self, messages: list, tools: list = None, stream: bool = False):
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if stream:
            kwargs["stream"] = True
        return self.client.chat.completions.create(**kwargs)

    def chat_with_retry(self, messages: list, retries: int = 3, delay: int = 2):
        for attempt in range(retries):
            try:
                return self.chat(messages)
            except RateLimitError:
                if attempt < retries - 1:
                    time.sleep(delay * (attempt + 1))
                else:
                    raise

    def stream_chat(self, messages: list):
        response = self.chat(messages, stream=True)
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
