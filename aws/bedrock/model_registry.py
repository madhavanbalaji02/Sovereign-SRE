"""
Bedrock Model Registry
======================
Canonical model IDs for Amazon Bedrock.
Use haiku by default; switch to sonnet only for final code-fix generation.

# BEDROCK COST: Claude Haiku = $0.00025/1K input tokens, $0.00125/1K output
# A typical SRE pipeline run = ~5K tokens total = ~$0.008 per incident
# 100 incidents/month = ~$0.80. Well within $100 budget.
"""

MODELS: dict[str, str] = {
    "haiku":   "anthropic.claude-haiku-4-5-20251001",
    "sonnet":  "anthropic.claude-sonnet-4-20250514",
    "llama3":  "meta.llama3-3-70b-instruct-v1:0",
    "titan":   "amazon.titan-text-express-v1",
}

DEFAULT_MODEL = "haiku"
CODE_FIX_MODEL = "sonnet"  # upgraded model for final patch generation


def get_model(name: str) -> str:
    """Return the Bedrock model ID for a friendly name. Falls back to haiku."""
    return MODELS.get(name, MODELS[DEFAULT_MODEL])
