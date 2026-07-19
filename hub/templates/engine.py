"""Motor de chat del agente: mensaje → LLM → tools → LLM → respuesta."""
from __future__ import annotations

import json
import re
from pathlib import Path

import agent_config as config
from llm.factory import build_adapter
from llm.prompts import build_system_prompt
from memory import session as session_store
from tools import registry
from tools.orchestrator import ToolOrchestrator, is_confirmation_message, mark_confirmed

MAX_TOOL_ROUNDS = 6
_DATA_DIR = config.AGENT_DIR / "data"
_ATT_PATTERN = re.compile(r'\[Adjuntos:\s*([^\]]+)\]')


def _inject_attachments(message: str) -> str:
    """Reemplaza [Adjuntos: f1, f2] con el contenido extraído de cada archivo."""
    match = _ATT_PATTERN.search(message)
    if not match:
        return message

    filenames = [f.strip() for f in match.group(1).split(",")]
    blocks: list[str] = []
    for fname in filenames:
        extracted = _DATA_DIR / f"{fname}.extracted.txt"
        if extracted.exists():
            content = extracted.read_text(encoding="utf-8", errors="replace")
            blocks.append(f"=== {fname} ===\n{content}\n=== fin ===")
        else:
            blocks.append(f"[Archivo adjunto: {fname}]")

    replacement = "\n\n".join(blocks)
    return _ATT_PATTERN.sub(replacement, message)


async def process_message(message: str, session_id: str | None, user_id: str = "default",
                          model_ref: str | None = None) -> dict:
    if not session_id:
        session_id = await session_store.create_session(user_id)

    system = build_system_prompt()
    history = await session_store.get_history(session_id)
    expanded = _inject_attachments(message)
    await session_store.add_message(session_id, "user", message)
    history.append({"role": "user", "content": expanded})

    tools_cfg = config.get("tools", {}) or {}
    tools = registry.tools_for_llm(tools_cfg.get("allow", ["*"]), tools_cfg.get("deny", []))

    # Si el mensaje es una confirmación, activar el gate para tools pendientes
    if is_confirmation_message(message):
        # Marcar todas las dangerous tools como confirmadas para esta sesión
        from tools.registry import all_tools
        for t in all_tools():
            if t.requires_confirm:
                mark_confirmed(session_id, t.name)

    # #11: si el chat manda un ref de modelo, se usa ese (sin reiniciar el agente).
    adapter = build_adapter(model_ref)
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
    # #7: contexto = tokens del prompt enviado al modelo (lo que "se llena")
    llm_cfg = config.get("llm", {}) or {}
    context_limit = int(llm_cfg.get("num_ctx", 8192))
    return {
        "session_id": session_id,
        "reply": final,
        "tools_used": tools_used,
        "tokens_used": response.output_tokens if response else 0,
        "context_tokens": response.input_tokens if response else 0,
        "context_limit": context_limit,
    }
