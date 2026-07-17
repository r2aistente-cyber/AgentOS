"""Motor de chat: recibe mensaje, llama LLM, ejecuta tools, devuelve respuesta."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from backend.llm.adapter import LLMResponse, ToolCall
from backend.llm.ollama import OllamaAdapter
from backend.llm.prompts import build_system_prompt, load_specialty
from backend.memory import session as session_store
from backend.tools import registry
from backend.tools.orchestrator import ToolOrchestrator

MAX_TOOL_ROUNDS = 6  # evitar loops infinitos


async def process_message(
    message: str,
    session_id: str | None,
    user_id: str = "xavier",
    specialty_id: str = "core",
    level: int = 3,
) -> dict:
    """Procesa un mensaje y devuelve la respuesta final."""

    # 1. Sesión
    if not session_id:
        session_id = await session_store.create_session(user_id, specialty_id)

    # 2. Especialidad + system prompt
    specialty = load_specialty(specialty_id)
    system = build_system_prompt(specialty)

    # 3. Historial
    history = await session_store.get_history(session_id)

    # 4. Guardar mensaje del usuario
    await session_store.add_message(session_id, "user", message)
    history.append({"role": "user", "content": message})

    # 5. Tools disponibles
    allowed = specialty.get("tools", {}).get("allow", ["*"])
    denied = specialty.get("tools", {}).get("deny", [])
    tools = [t for t in registry.tools_for_llm(allowed if allowed != ["*"] else None)
             if t["function"]["name"] not in denied]

    # 6. Loop LLM → tool → LLM
    adapter = OllamaAdapter()
    orchestrator = ToolOrchestrator(user_id, level, session_id)
    tools_used: list[str] = []
    messages = list(history)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await adapter.chat(messages, tools=tools or None, system=system)

        if not response.has_tool_calls:
            break

        # Ejecutar cada tool call
        tool_results = []
        for tc in response.tool_calls:
            tools_used.append(tc.name)
            result = await orchestrator.execute(tc)
            tool_results.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
                "tool_call_id": tc.id,
            })

        # Agregar respuesta del asistente con tool calls al historial
        messages.append({"role": "assistant", "content": response.content or "", "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
            for tc in response.tool_calls
        ]})
        messages.extend(tool_results)

    # 7. Guardar respuesta final
    final_content = response.content
    await session_store.add_message(session_id, "assistant", final_content, tools_used, response.output_tokens)

    return {
        "session_id": session_id,
        "reply": final_content,
        "tools_used": tools_used,
        "tokens": response.output_tokens,
    }
