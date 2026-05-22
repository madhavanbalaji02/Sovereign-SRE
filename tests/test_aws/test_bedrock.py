"""Tests for aws/bedrock/ — client, model_registry, fallback."""

import os
import pytest


def test_model_registry_defaults():
    from aws.bedrock.model_registry import get_model, MODELS, DEFAULT_MODEL
    assert "haiku" in MODELS
    assert "sonnet" in MODELS
    assert "llama3" in MODELS
    assert "titan" in MODELS
    assert get_model("haiku") == MODELS["haiku"]
    assert get_model("unknown-key") == MODELS[DEFAULT_MODEL]


def test_model_registry_get_model_known():
    from aws.bedrock.model_registry import get_model
    assert "claude-haiku" in get_model("haiku")
    assert "claude-sonnet" in get_model("sonnet")


def test_fallback_uses_groq_when_bedrock_disabled(monkeypatch):
    """When BEDROCK_ENABLED=false, fallback should report using Groq."""
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_TO_OLLAMA", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    # Reload config to pick up env change
    import importlib
    import aws.config as cfg
    importlib.reload(cfg)

    from aws.bedrock.fallback import BedrockLLMWithFallback

    fb = BedrockLLMWithFallback()
    # _try_bedrock should return None since BEDROCK_ENABLED=false
    assert fb._try_bedrock() is None


def test_fallback_raises_when_both_disabled(monkeypatch):
    monkeypatch.setenv("BEDROCK_ENABLED", "false")
    monkeypatch.setenv("BEDROCK_FALLBACK_TO_OLLAMA", "false")

    import importlib
    import aws.config as cfg
    importlib.reload(cfg)

    from aws.bedrock.fallback import BedrockLLMWithFallback
    fb = BedrockLLMWithFallback()
    fb._using_bedrock = None  # reset

    with pytest.raises(RuntimeError, match="BEDROCK_FALLBACK_TO_OLLAMA=false"):
        fb._get_client()


def test_bedrock_client_build_messages():
    """BedrockLLM._build_messages should structure payload correctly."""
    from aws.bedrock.client import BedrockLLM
    client = BedrockLLM.__new__(BedrockLLM)
    client._model_id = "anthropic.claude-haiku-4-5-20251001"
    client._max_tokens = 512
    client._temperature = 0.1
    client._client = None
    client._last_usage = {}

    messages, system = client._build_messages("Hello", "You are an SRE")
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "Hello"
    assert system[0]["text"] == "You are an SRE"

    messages2, system2 = client._build_messages("Hi", None)
    assert system2 == []
