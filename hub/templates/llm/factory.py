"""Selecciona el adapter LLM según config.llm.provider o un ref explícito.

Un ref de modelo es "provider/model" (p.ej. "ollama/qwen2.5:latest",
"opencode-go/deepseek-v4-flash"). Se parte por el PRIMER "/" porque el id del
modelo puede contener "/". Sin ref, se usa el provider/model del config.
"""
from __future__ import annotations

import agent_config as config
from llm.adapter import LLMAdapter


def parse_ref(ref: str) -> tuple[str | None, str | None]:
    if not ref:
        return None, None
    if "/" in ref:
        provider, model = ref.split("/", 1)
        return provider.lower(), model
    return None, ref


def build_adapter(model_ref: str | None = None) -> LLMAdapter:
    provider: str | None = None
    model: str | None = None
    if model_ref:
        provider, model = parse_ref(model_ref)
    if not provider:
        provider = (config.get("llm.provider", "ollama") or "ollama").lower()

    if provider == "ollama":
        from llm.ollama import OllamaAdapter
        return OllamaAdapter(model=model)
    if provider == "anthropic":
        from llm.anthropic import AnthropicAdapter
        return AnthropicAdapter(model=model)
    if provider in ("openai", "opencode", "opencode-go", "custom"):
        from llm.openai_compat import OpenAICompatAdapter
        return OpenAICompatAdapter(provider, model=model)
    if provider == "mock":
        from llm.mock import MockAdapter
        return MockAdapter()

    raise ValueError(f"Proveedor LLM desconocido: {provider}")
