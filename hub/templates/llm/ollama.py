"""Adapter Ollama (function calling nativo)."""
from __future__ import annotations

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall


class OllamaAdapter(LLMAdapter):
    def __init__(self) -> None:
        self._host = config.get("llm.host", "http://localhost:11434")
        self._model = config.get("llm.model", "qwen2.5:latest")
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self._host}/api/tags")
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
            "stream": False,
            "options": {"temperature": self._temperature, "num_predict": self._max_tokens},
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self._host}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        msg = data.get("message", {})
        tool_calls = [
            ToolCall(id=tc.get("id", f"call_{i}"),
                     name=tc["function"]["name"],
                     arguments=tc["function"].get("arguments", {}))
            for i, tc in enumerate(msg.get("tool_calls", []))
        ]
        return LLMResponse(
            content=msg.get("content", ""),
            tool_calls=tool_calls,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
        )
