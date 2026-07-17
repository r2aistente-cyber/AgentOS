"""Ollama adapter usando function calling nativo."""
from __future__ import annotations

import httpx

from backend.llm.adapter import LLMAdapter, LLMResponse, ToolCall
import backend.config as config


class OllamaAdapter(LLMAdapter):
    def __init__(self):
        self._host = config.get("llm.ollama.host") or config.get("llm.host") or "http://localhost:11434"
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

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }

        if system:
            payload["messages"] = [{"role": "system", "content": system}, *messages]

        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{self._host}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        msg = data.get("message", {})
        content = msg.get("content", "")
        raw_calls = msg.get("tool_calls", [])

        tool_calls = [
            ToolCall(
                id=tc.get("id", f"call_{i}"),
                name=tc["function"]["name"],
                arguments=tc["function"].get("arguments", {}),
            )
            for i, tc in enumerate(raw_calls)
        ]

        usage = data.get("prompt_eval_count", 0), data.get("eval_count", 0)

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            input_tokens=usage[0],
            output_tokens=usage[1],
        )
