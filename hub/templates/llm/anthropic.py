"""Adapter Anthropic (Claude) — traduce el formato interno estilo OpenAI
al formato de la Messages API de Claude (system aparte, input_schema, bloques
tool_use / tool_result).
"""
from __future__ import annotations

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall

_API = "https://api.anthropic.com/v1/messages"
_VERSION = "2023-06-01"


class AnthropicAdapter(LLMAdapter):
    def __init__(self) -> None:
        self._base = (config.get("llm.host") or "https://api.anthropic.com").rstrip("/")
        self._model = config.get("llm.model", "claude-opus-4-8")
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)
        self._key = config.get_secret("anthropic_key")

    def _headers(self) -> dict:
        if not self._key:
            raise RuntimeError("ANTHROPIC_API_KEY no configurada")
        return {
            "x-api-key": self._key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }

    async def ping(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": _to_anthropic_messages(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = _to_anthropic_tools(tools)

        url = f"{self._base}/v1/messages" if self._base != "https://api.anthropic.com" else _API
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()

        text_parts, tool_calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}) or {},
                ))
        usage = data.get("usage", {})
        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )


def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    out = []
    for t in tools:
        fn = t.get("function", t)
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return out


def _to_anthropic_messages(messages: list[dict]) -> list[dict]:
    """Convierte mensajes estilo OpenAI a formato Claude, agrupando tool_results."""
    result: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results():
        if pending_tool_results:
            result.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for msg in messages:
        role = msg.get("role")
        if role == "tool":
            pending_tool_results.append({
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id", ""),
                "content": str(msg.get("content", "")),
            })
            continue
        flush_tool_results()
        if role == "assistant":
            blocks = []
            if msg.get("content"):
                blocks.append({"type": "text", "text": msg["content"]})
            for tc in msg.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    import json
                    try:
                        args = json.loads(args or "{}")
                    except json.JSONDecodeError:
                        args = {}
                blocks.append({"type": "tool_use", "id": tc.get("id", ""),
                               "name": fn.get("name", ""), "input": args})
            result.append({"role": "assistant", "content": blocks or [{"type": "text", "text": ""}]})
        else:  # user (o system que se filtró antes)
            result.append({"role": "user", "content": str(msg.get("content", ""))})

    flush_tool_results()
    return result
