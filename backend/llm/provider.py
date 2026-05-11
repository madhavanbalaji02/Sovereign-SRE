"""
LLM Provider Factory
====================
Switch providers by setting LLM_PROVIDER env var:
  groq   → Groq cloud (Llama 3.3 on LPU, default, free tier)
  grok   → xAI Grok API (grok-3-mini)
  claude → Anthropic Claude (best reasoning)
"""

import os


def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", "groq")
    if provider == "groq":
        from backend.llm.groq_client import GroqClient
        return GroqClient()
    elif provider == "grok":
        from backend.llm.grok_client import GrokClient
        return GrokClient()
    elif provider == "claude":
        from backend.llm.claude_client import ClaudeClient
        return ClaudeClient()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
