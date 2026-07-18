"""Adapter mock — para dev y tests sin LLM real. Si el último mensaje del usuario
menciona una tool disponible, la llama una vez; si no, responde con un eco.
"""
from __future__ import annotations

from llm.adapter import LLMAdapter, LLMResponse, ToolCall


class MockAdapter(LLMAdapter):
    async def ping(self) -> bool:
        return True

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        # ¿Ya ejecutamos una tool? (hay un mensaje role="tool" en el historial)
        already_used_tool = any(m.get("role") == "tool" for m in messages)
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        text = str(last_user.get("content", "")) if last_user else ""

        if tools and not already_used_tool:
            # Si el usuario nombra una tool, llámala
            for t in tools:
                name = t.get("function", {}).get("name", "")
                if name and name in text:
                    return LLMResponse(
                        content="",
                        tool_calls=[ToolCall(id="mock_1", name=name, arguments={})],
                        output_tokens=5,
                    )
        return LLMResponse(content=f"[mock] recibí: {text}", output_tokens=8)
