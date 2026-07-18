"""Adapter Ollama (function calling nativo)."""
from __future__ import annotations

import json

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall


def _to_ollama_messages(messages: list[dict]) -> list[dict]:
    """Normaliza el historial interno (estilo OpenAI) al formato de Ollama.

    Ollama exige que `tool_calls[].function.arguments` sea un OBJETO (no un
    string JSON) y no usa `tool_call_id`; los resultados de tool van como
    role=tool con `content` (+ `tool_name` opcional). Sin esto, la 2ª ronda
    del loop de tools rompía con 400 Bad Request.
    """
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            tcs = []
            for tc in m["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (ValueError, TypeError):
                        args = {}
                tcs.append({"function": {"name": fn.get("name"), "arguments": args or {}}})
            out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": tcs})
        elif role == "tool":
            entry = {"role": "tool", "content": m.get("content", "")}
            if m.get("name"):
                entry["tool_name"] = m["name"]
            out.append(entry)
        else:
            out.append({"role": role, "content": m.get("content", "")})
    return out


class OllamaAdapter(LLMAdapter):
    def __init__(self) -> None:
        self._host = config.get("llm.host", "http://localhost:11434")
        self._model = config.get("llm.model", "qwen2.5:latest")
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)
        self._num_ctx = config.get("llm.num_ctx", 8192)
        # Mantener el modelo cargado en memoria para no pagar el cold-start (~80s)
        # en cada primer mensaje. Configurable con llm.keep_alive.
        self._keep_alive = config.get("llm.keep_alive", "30m")

    async def warmup(self) -> None:
        """Carga el modelo en memoria (se llama en background al arrancar)."""
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                await client.post(f"{self._host}/api/chat", json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "keep_alive": self._keep_alive,
                    "options": {"num_predict": 1},
                })
        except Exception:
            pass

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{self._host}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        msgs = _to_ollama_messages(messages)
        if system:
            msgs = [{"role": "system", "content": system}, *msgs]
        payload: dict = {
            "model": self._model,
            "messages": msgs,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
                "num_ctx": self._num_ctx,
            },
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
