"""Catálogo estático de modelos por proveedor — para el Hub (no para agentes).

Sirve para que el frontend muestre dropdowns en vez de campos de texto libre.
Proveedores sin catálogo fijo (Ollama, custom) = None.
"""
from __future__ import annotations

# Catálogo de OpenCode Go (suscripción Go, usa OPENCODE_API_KEY).
OPENGODE_GO_MODELS = [
    "grok-4.5",
    "glm-5.2",
    "glm-5.1",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "mimo-v2.5",
    "mimo-v2.5-pro",
    "minimax-m3",
    "minimax-m2.7",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
]

# Catálogo de OpenCode Zen (suscripción Zen, usa OPENCODE_API_KEY).
OPENGODE_ZEN_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "gpt-5.5",
    "gpt-5.3",
    "gpt-4.1",
    "gemini-3-pro",
    "gemini-3-flash",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
]

# Catálogo estático de OpenAI
OPENAI_MODELS = [
    "gpt-5.5",
    "gpt-5.3",
    "gpt-4.1",
    "gpt-4o",
    "gpt-4o-mini",
    "o3",
    "o4-mini",
]

# Catálogo estático de Anthropic
ANTHROPIC_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

PROVIDER_CATALOGS: dict[str, list[str] | None] = {
    "opencode-go": OPENGODE_GO_MODELS,
    "opencode": OPENGODE_ZEN_MODELS,
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "ollama": None,
    "mock": ["mock-default"],
    "custom": None,
}


def get_catalog(provider: str) -> list[str] | None:
    return PROVIDER_CATALOGS.get(provider)
