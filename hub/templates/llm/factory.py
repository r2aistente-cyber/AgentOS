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


def _find_model_key(provider: str, model: str | None) -> str | None:
    """Busca api_key en llm.models para el provider/model dado.

    Primero intenta match exacto provider+model, luego solo provider.
    Retorna None si no hay key guardada para ese provider.
    """
    models_list: list[dict] = config.get("llm.models") or []
    # Exact match first
    if model:
        for m in models_list:
            if m.get("provider") == provider and m.get("model") == model and m.get("api_key"):
                return m["api_key"]
    # Provider-only match
    for m in models_list:
        if m.get("provider") == provider and m.get("api_key"):
            return m["api_key"]
    # Fallback: primary llm.api_key when provider matches primary
    if config.get("llm.provider", "") == provider:
        return config.get("llm.api_key")
    return None


def _make_adapter(provider: str, model: str | None, api_key: str | None) -> LLMAdapter:
    if provider == "ollama":
        from llm.ollama import OllamaAdapter
        return OllamaAdapter(model=model)
    if provider == "anthropic":
        from llm.anthropic import AnthropicAdapter
        return AnthropicAdapter(model=model, api_key=api_key)
    if provider in ("openai", "opencode", "opencode-go", "custom"):
        from llm.openai_compat import OpenAICompatAdapter
        return OpenAICompatAdapter(provider, model=model, api_key=api_key)
    if provider == "claude-cli":
        from llm.claude_cli import ClaudeCliAdapter
        return ClaudeCliAdapter(model=model)
    if provider == "mock":
        from llm.mock import MockAdapter
        return MockAdapter()
    raise ValueError(f"Proveedor LLM desconocido: {provider}")


def build_adapter(model_ref: str | None = None) -> LLMAdapter:
    provider: str | None = None
    model: str | None = None
    if model_ref:
        provider, model = parse_ref(model_ref)
    if not provider:
        provider = (config.get("llm.provider", "ollama") or "ollama").lower()

    api_key = _find_model_key(provider, model)
    return _make_adapter(provider, model, api_key)


class FallbackAdapter(LLMAdapter):
    """Intenta adapters en orden; si uno falla con error retriable pasa al siguiente."""

    _RETRIABLE = {429, 500, 502, 503, 504}

    def __init__(self, adapters: list[LLMAdapter]) -> None:
        self._adapters = adapters

    async def chat(self, messages, tools=None, system=None) -> "LLMResponse":
        import httpx
        last_exc: Exception | None = None
        for adapter in self._adapters:
            try:
                return await adapter.chat(messages, tools, system)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in self._RETRIABLE:
                    last_exc = exc
                    continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                continue
        raise last_exc  # type: ignore[misc]

    async def ping(self) -> bool:
        for adapter in self._adapters:
            try:
                if await adapter.ping():
                    return True
            except Exception:
                continue
        return False


def build_adapter_with_fallback(model_ref: str | None = None) -> LLMAdapter:
    """Construye el adapter primario y añade fallbacks desde llm.models si el usuario
    no especificó un modelo concreto (model_ref=None)."""
    primary = build_adapter(model_ref)
    if model_ref:
        return primary  # selección explícita: sin fallback

    models_list: list[dict] = config.get("llm.models") or []
    if len(models_list) <= 1:
        return primary  # solo un modelo configurado

    fallbacks: list[LLMAdapter] = [primary]
    primary_provider = (config.get("llm.provider", "") or "").lower()
    primary_model = config.get("llm.model", "") or ""

    for entry in models_list:
        p = (entry.get("provider") or "").lower()
        m = entry.get("model") or ""
        if p == primary_provider and m == primary_model:
            continue  # ya está como primario
        try:
            api_key = _find_model_key(p, m)
            fallbacks.append(_make_adapter(p, m, api_key))
        except Exception:
            continue

    if len(fallbacks) == 1:
        return primary
    return FallbackAdapter(fallbacks)
