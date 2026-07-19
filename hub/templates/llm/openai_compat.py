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
    def __init__(self, provider: str = "openai", model: str | None = None,
                 api_key: str | None = None) -> None:
        base, secret_name = _PROVIDERS.get(provider, (None, "openai_key"))
        # llm.host solo se respeta para proveedores "custom" (sin URL hardcodeada).
        # Para openai/opencode/opencode-go se usa siempre la URL canónica.
        custom_host = config.get("llm.host") if provider not in _PROVIDERS else None
        self._base = (custom_host or base or "https://api.openai.com/v1").rstrip("/")
        # #9: el modelo puede venir como "provider/model" — extraer solo el nombre
        raw_model = model or config.get("llm.model", "gpt-4o-mini")
        if raw_model and "/" in raw_model:
            raw_model = raw_model.split("/", 1)[1]
        self._model = raw_model
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)
        # api_key explícita (del models list) tiene precedencia sobre get_secret
        self._key = api_key or config.get_secret(secret_name)
        # cache del proveedor para la lógica de api_key específica
        self._provider = provider

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

        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{self._base}/chat/completions",
                                  headers=self._headers(), json=payload)
            # Some reasoning models (Kimi K2, etc.) only accept temperature=1.
            # Retry once with temp=1 before propagating the 400.
            if r.status_code == 400 and self._temperature != 1:
                payload["temperature"] = 1
                r = await client.post(f"{self._base}/chat/completions",
                                      headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]["message"]
        finish_reason = data["choices"][0].get("finish_reason", "")
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

        content = choice.get("content") or ""

        # Si se cortó por max_tokens, hacer una continuación
        if finish_reason == "length" and content and not tool_calls:
            cont_msgs = list(msgs) + [{"role": "assistant", "content": content}]
            cont_msgs.append({"role": "user", "content": "[Continúa desde donde te cortaste, sin repetir lo anterior]"})
            cont_payload = {**payload, "messages": cont_msgs}
            async with httpx.AsyncClient(timeout=300) as client:
                r2 = await client.post(f"{self._base}/chat/completions",
                                       headers=self._headers(), json=cont_payload)
                if r2.status_code == 200:
                    cont_data = r2.json()
                    cont_content = cont_data["choices"][0]["message"].get("content") or ""
                    content = content + cont_content
                    usage2 = cont_data.get("usage", {})
                    data.setdefault("usage", {})
                    data["usage"]["completion_tokens"] = (
                        data["usage"].get("completion_tokens", 0) + usage2.get("completion_tokens", 0)
                    )

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
