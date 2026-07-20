"""Motor de chat del agente: mensaje → LLM → tools → LLM → respuesta.
Usa RAG para inyectar solo los chunks de knowledge relevantes al mensaje.
"""
from __future__ import annotations

import json

import agent_config as config
from llm.factory import build_adapter
from llm.prompts import build_system_prompt
from memory import session as session_store
from rag import indexer as rag_indexer
from rag import retriever as rag_retriever
from tools import registry
from tools.orchestrator import ToolOrchestrator

MAX_TOOL_ROUNDS = 5

_rag_ready = False


def _ensure_rag_indexed() -> None:
    global _rag_ready
    if not _rag_ready and rag_indexer.has_knowledge():
        rag_indexer.index()
        _rag_ready = True


async def process_message(message: str, session_id: str | None, user_id: str = "default",
                          model_ref: str | None = None) -> dict:
    if not session_id:
        session_id = await session_store.create_session(user_id)

    _ensure_rag_indexed()
    base_prompt = build_system_prompt()
    rag_context = rag_retriever.retrieve(message)
    system = f"{base_prompt}\n\n{rag_context}" if rag_context else base_prompt
    history = await session_store.get_history(session_id)
    # Limitar historial a los últimos 20 mensajes para no saturar el LLM
    history = history[-20:]
    await session_store.add_message(session_id, "user", message)
    history.append({"role": "user", "content": message})

    tools_cfg = config.get("tools", {}) or {}
    tools = registry.tools_for_llm(tools_cfg.get("allow", ["*"]), tools_cfg.get("deny", []))

    adapter = build_adapter(model_ref)
    orchestrator = ToolOrchestrator(session_id)
    tools_used: list[str] = []
    messages = list(history)
    response = None
    error_msg: str | None = None

    try:
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

        # Si el loop agotó los rounds con tool calls pendientes, pedir respuesta final
        if response and response.has_tool_calls:
            messages.append({"role": "user", "content": "Resume en texto todo lo que encontraste y concluye tu respuesta."})
            response = await adapter.chat(messages, tools=None, system=system)

        # Si la respuesta sigue vacía (modelo devolvió solo DSML que fue stripeado), forzar resumen
        if response and not response.content and not response.has_tool_calls:
            messages.append({"role": "user", "content": "Tu respuesta anterior estaba vacía. Responde ahora en texto plano con lo que encontraste."})
            response = await adapter.chat(messages, tools=None, system=system)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("LLM error: %s", exc, exc_info=True)
        error_msg = f"⚠️ Error del proveedor LLM: {type(exc).__name__}: {exc}"

    final = error_msg or (response.content if response else "")
    await session_store.add_message(session_id, "assistant", final, tools_used,
                                    response.output_tokens if response else 0)
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
