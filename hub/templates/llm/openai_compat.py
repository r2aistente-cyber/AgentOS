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
_SEP = '｜｜'  # ｜｜ fullwidth vertical line U+FF5C (no pipe normal)
_DSML_BLOCK = re.compile(
    rf'<{_SEP}DSML{_SEP}tool_calls>(.*?)</{_SEP}DSML{_SEP}tool_calls>',
    re.DOTALL,
)
_DSML_INVOKE = re.compile(
    rf'<{_SEP}DSML{_SEP}invoke\s+name="([^"]+)">(.*?)</{_SEP}DSML{_SEP}invoke>',
    re.DOTALL,
)
_DSML_PARAM = re.compile(
    rf'<{_SEP}DSML{_SEP}parameter\s+name="([^"]+)"\s+string="([^"]+)">(.*?)</{_SEP}DSML{_SEP}parameter>',
    re.DOTALL,
)


def _has_dsml(content: str) -> bool:
    return f'<{_SEP}DSML{_SEP}' in content


def _parse_dsml(content: str) -> tuple[str, list[ToolCall]]:
    """Extrae tool calls del formato DSML de DeepSeek embebido en content.

    Retorna (content_limpio, tool_calls). Maneja bloques completos e incompletos.
    """
    if not _has_dsml(content):
        return content, []

    tool_calls: list[ToolCall] = []
    block_match = _DSML_BLOCK.search(content)

    if block_match:
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

    # Siempre limpiar: bloques completos primero, luego residuos/truncados
    clean = _DSML_BLOCK.sub("", content)
    clean = re.sub(rf'<{_SEP}DSML{_SEP}.*', '', clean, flags=re.DOTALL).strip()
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

        # Limpiar DSML del content siempre — puede aparecer mezclado con texto normal
        # incluso cuando ya hubo tool_calls estándar en rondas anteriores
        if content:
            if not tool_calls:
                # Sin tool_calls estándar: parsear DSML como tool_calls reales
                content, tool_calls = _parse_dsml(content)
            else:
                # Con tool_calls estándar: solo limpiar el markup del texto visible
                content, _ = _parse_dsml(content)

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
                    cont_data = r2.json()
                    cont_content = cont_data["choices"][0]["message"].get("content") or ""
                    content = content + cont_content
                    usage2 = cont_data.get("usage", {})
                    data.setdefault("usage", {})
                    data["usage"]["completion_tokens"] = (
                        data["usage"].get("completion_tokens", 0)
                        + usage2.get("completion_tokens", 0)
                    )

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )
