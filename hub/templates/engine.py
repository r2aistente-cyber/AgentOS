"""Motor de chat del agente: mensaje → LLM → tools → LLM → respuesta."""
from __future__ import annotations

import json

import agent_config as config
from llm.factory import build_adapter
from llm.prompts import build_system_prompt
from memory import session as session_store
from tools import registry
from tools.orchestrator import ToolOrchestrator

MAX_TOOL_ROUNDS = 6


async def process_message(message: str, session_id: str | None, user_id: str = "default") -> dict:
    if not session_id:
        session_id = await session_store.create_session(user_id)

    system = build_system_prompt()
    history = await session_store.get_history(session_id)
    await session_store.add_message(session_id, "user", message)
    history.append({"role": "user", "content": message})

    tools_cfg = config.get("tools", {}) or {}
    tools = registry.tools_for_llm(tools_cfg.get("allow", ["*"]), tools_cfg.get("deny", []))

    adapter = build_adapter()
    orchestrator = ToolOrchestrator(session_id)
    tools_used: list[str] = []
    messages = list(history)
    response = None

    for _ in range(MAX_TOOL_ROUNDS):
        response = await adapter.chat(messages, tools=tools or None, system=system)
        if not response.has_tool_calls:
            break

        messages.append({
            "role": "assistant",
            "content": response.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)}}
                for tc in response.tool_calls
            ],
        })
        for tc in response.tool_calls:
            tools_used.append(tc.name)
            result = await orchestrator.execute(tc)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.name,
                "content": json.dumps(result, ensure_ascii=False),
            })

    final = response.content if response else ""
    await session_store.add_message(session_id, "assistant", final, tools_used,
                                    response.output_tokens if response else 0)
    return {
        "session_id": session_id,
        "reply": final,
        "tools_used": tools_used,
        "tokens_used": response.output_tokens if response else 0,
    }
