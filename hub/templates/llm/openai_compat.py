"""Adapter para APIs compatibles con OpenAI: OpenAI, OpenCode, o cualquier
endpoint custom con base_url. El formato interno de mensajes ya es el de OpenAI.

Maneja también el formato DSML nativo de DeepSeek cuando el proxy no lo convierte
al formato estándar de tool_calls.
"""
from __future__ import annotations

import json
import re
import uuid

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall

_PROVIDERS = {
    "openai":      ("https://api.openai.com/v1", "openai_key"),
    "opencode":    ("https://opencode.ai/zen/v1", "opencode_key"),
    "opencode-go": ("https://opencode.ai/zen/go/v1", "opencode_key"),
}

# Detecta el bloque DSML completo de tool_calls de DeepSeek
_DSML_BLOCK = re.compile(
    r'<\|\|DSML\|\|tool_calls>(.*?)</\|\|DSML\|\|tool_calls>',
    re.DOTALL,
)
# Extrae cada invoke dentro del bloque
_DSML_INVOKE = re.compile(
    r'<\|\|DSML\|\|invoke\s+name="([^"]+)">(.*?)</\|\|DSML\|\|invoke>',
    re.DOTALL,
)
# Extrae cada parameter dentro de un invoke
_DSML_PARAM = re.compile(
    r'<\|\|DSML\|\|parameter\s+name="([^"]+)"\s+string="([^"]+)">(.*?)</\|\|DSML\|\|parameter>',
    re.DOTALL,
)


def _parse_dsml(content: str) -> tuple[str, list[ToolCall]]:
    """Extrae tool calls del formato DSML de DeepSeek embebido en content.

    Retorna (content_limpio, tool_calls). Si no hay DSML, retorna el content
    original con lista vacía.
    """
    block_match = _DSML_BLOCK.search(content)
    if not block_match:
        return content, []

    tool_calls: list[ToolCall] = []
    block_text = block_match.group(1)

    for invoke in _DSML_INVOKE.finditer(block_text):
        fn_name = invoke.group(1)
        params_text = invoke.group(2)
        arguments: dict = {}

        for param in _DSML_PARAM.finditer(params_text):
            p_name = param.group(1)
            p_is_string = param.group(2).lower() == "true"
            p_value = param.group(3).strip()
            if p_is_string:
                arguments[p_name] = p_value
            else:
                try:
                    arguments[p_name] = json.loads(p_value)
                except (json.JSONDecodeError, ValueError):
                    arguments[p_name] = p_value

        tool_calls.append(ToolCall(
            id=f"dsml-{uuid.uuid4().hex[:8]}",
            name=fn_name,
            arguments=arguments,
        ))

    clean = _DSML_BLOCK.sub("", content).strip()
    return clean, tool_calls


class OpenAICompatAdapter(LLMAdapter):
    def __init__(self, provider: str = "openai", model: str | None = None,
                 api_key: str | None = None) -> None:
        base, secret_name = _PROVIDERS.get(provider, (None, "openai_key"))
        custom_host = config.get("llm.host") if provider not in _PROVIDERS else None
        self._base = (custom_host or base or "https://api.openai.com/v1").rstrip("/")
        raw_model = model or config.get("llm.model", "gpt-4o-mini")
        if raw_model and "/" in raw_model:
            raw_model = raw_model.split("/", 1)[1]
        self._model = raw_model
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)
        self._key = api_key or config.get_secret(secret_name)
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
            if r.status_code == 400 and self._temperature != 1:
                payload["temperature"] = 1
                r = await client.post(f"{self._base}/chat/completions",
                                      headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]["message"]
        finish_reason = data["choices"][0].get("finish_reason", "")

        # Parsear tool_calls en formato OpenAI estándar
        tool_calls: list[ToolCall] = []
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

        # Si no hay tool_calls estándar, buscar DSML nativo de DeepSeek en el content
        if not tool_calls and content:
            content, tool_calls = _parse_dsml(content)

        # Si se cortó por max_tokens y es texto puro (sin tools), continuar
        if finish_reason == "length" and content and not tool_calls:
            cont_msgs = list(msgs) + [
                {"role": "assistant", "content": content},
                {"role": "user", "content": "[continúa]"},
            ]
            cont_payload = {**payload, "messages": cont_msgs}
            cont_payload.pop("tools", None)
            async with httpx.AsyncClient(timeout=300) as client:
                r2 = await client.post(f"{self._base}/chat/completions",
                                       headers=self._headers(), json=cont_payload)
                if r2.status_code == 200:
                    cont_choice = r2.json()["choices"][0]
                    cont_content = cont_choice["message"].get("content") or ""
                    content = content + cont_content
                    usage2 = r2.json().get("usage", {})
                    data["usage"]["completion_tokens"] = (
                        data.get("usage", {}).get("completion_tokens", 0)
                        + usage2.get("completion_tokens", 0)
                    )

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
