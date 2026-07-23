"""Motor de chat del agente: mensaje → LLM → tools → LLM → respuesta.
Usa RAG para inyectar solo los chunks de knowledge relevantes al mensaje.
"""
from __future__ import annotations

import asyncio
import json
import logging

import agent_config as config
from llm.factory import build_adapter_with_fallback as build_adapter
from llm.prompts import build_system_prompt
from memory import session as session_store
from rag import indexer as rag_indexer
from rag import retriever as rag_retriever
from tools import registry
from tools.orchestrator import ToolOrchestrator, is_confirmation_message, mark_confirmed

log = logging.getLogger(__name__)

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

    # Si el mensaje es una confirmación, activar el token y no mandar al LLM
    if is_confirmation_message(message):
        # Marcar todas las tools pendientes de confirmación como aprobadas
        for tool_name in ("exec_command", "write_file", "run_python"):
            mark_confirmed(session_id, tool_name)
        await session_store.add_message(session_id, "user", message)
        # Recuperar último mensaje del asistente para re-ejecutar
        history = await session_store.get_history(session_id)
        history = history[-20:]
        # Continuar el flujo normalmente — el LLM reintentará la tool call con el token activo
    else:
        history = await session_store.get_history(session_id)
        history = history[-20:]
        await session_store.add_message(session_id, "user", message)

    base_prompt = build_system_prompt()
    try:
        # retrieve() es sync y puede tardar — corre en thread para no bloquear el event loop
        rag_context = await asyncio.to_thread(rag_retriever.retrieve, message)
    except Exception:
        rag_context = ""
    system = f"{base_prompt}\n\n{rag_context}" if rag_context else base_prompt

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
            failed_tools: list[str] = []
            for tc in response.tool_calls:
                tools_used.append(tc.name)
                result = await orchestrator.execute(tc)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": json.dumps(result, ensure_ascii=False),
                })
                if not result.get("success", True):
                    failed_tools.append(tc.name)

            # Si alguna tool falló, forzar al LLM a reconocer el error antes de continuar
            if failed_tools:
                messages.append({
                    "role": "user",
                    "content": (
                        f"SISTEMA: Las siguientes herramientas FALLARON: {', '.join(failed_tools)}. "
                        "Debes reportar los errores exactos al usuario y detenerte. "
                        "NO continúes como si hubieran funcionado. NO inventes resultados."
                    ),
                })

        # Si el loop agotó los rounds con tool calls pendientes, pedir respuesta final
        if response and response.has_tool_calls:
            messages.append({"role": "user", "content": "Resume en texto todo lo que encontraste y concluye tu respuesta."})
            response = await adapter.chat(messages, tools=None, system=system)

        # Si la respuesta está vacía, forzar resumen
        if response and not response.content and not response.has_tool_calls:
            messages.append({"role": "user", "content": "Tu respuesta anterior estaba vacía. Responde en texto plano con lo que encontraste."})
            response = await adapter.chat(messages, tools=None, system=system)

    except Exception as exc:
        log.error("LLM error: %s", exc, exc_info=True)
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
