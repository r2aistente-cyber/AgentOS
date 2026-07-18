"""Adapter para APIs compatibles con OpenAI: OpenAI, OpenCode, o cualquier
endpoint custom con base_url. El formato interno de mensajes ya es el de OpenAI.
"""
from __future__ import annotations

import json

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall

# base_url y secreto por proveedor. opencode-go comparte credencial y host con
# opencode (catálogo Go); el modelo lo distingue (ver providers/opencode-go).
_PROVIDERS = {
    "openai":      ("https://api.openai.com/v1", "openai_key"),
    "opencode":    ("https://opencode.ai/zen/v1", "opencode_key"),
    "opencode-go": ("https://opencode.ai/zen/go/v1", "opencode_key"),
}


class OpenAICompatAdapter(LLMAdapter):
    def __init__(self, provider: str = "openai", model: str | None = None) -> None:
        base, secret_name = _PROVIDERS.get(provider, (None, "openai_key"))
        self._base = config.get("llm.host") or base or "https://api.openai.com/v1"
        self._base = self._base.rstrip("/")
        self._model = model or config.get("llm.model", "gpt-4o-mini")
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)
        self._key = config.get_secret(secret_name)

    def _headers(self) -> dict:
        if not self._key:
            raise RuntimeError("API key no configurada para el proveedor LLM")
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base}/models", headers=self._headers())
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        payload: dict = {
            "model": self._model,
            "messages": msgs,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self._base}/chat/completions",
                                  headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]["message"]
        tool_calls = []
        for tc in choice.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args))

        usage = data.get("usage", {})
        return LLMResponse(
            content=choice.get("content") or "",
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
