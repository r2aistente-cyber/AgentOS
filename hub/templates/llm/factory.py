"""Selecciona el adapter LLM según config.llm.provider."""
from __future__ import annotations

import agent_config as config
from llm.adapter import LLMAdapter


def build_adapter() -> LLMAdapter:
    provider = (config.get("llm.provider", "ollama") or "ollama").lower()

    if provider == "ollama":
        from llm.ollama import OllamaAdapter
        return OllamaAdapter()
    if provider == "anthropic":
        from llm.anthropic import AnthropicAdapter
        return AnthropicAdapter()
    if provider in ("openai", "opencode", "custom"):
        from llm.openai_compat import OpenAICompatAdapter
        return OpenAICompatAdapter(provider)
    if provider == "mock":
        from llm.mock import MockAdapter
        return MockAdapter()

    raise ValueError(f"Proveedor LLM desconocido: {provider}")
