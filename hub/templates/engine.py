"""Motor FSM del agente — inspirado en OpenClaw.

Estados: THINKING → EXECUTING → (loop) → RESPONDING
                             ↘ WAITING_CONFIRM (si tool requiere confirmación)

Principios clave:
  - El runtime controla el loop (no el LLM).
  - `break` en Python cuando las tools fallan; NO se inyectan prompts de "detente".
  - Confirmaciones re-ejecutan la ToolCall preservada (no piden al LLM que recuerde).
  - ToolResult.success lo determina el código, nunca el modelo.
  - Máximo MAX_TOOL_ROUNDS para evitar loops infinitos.
"""
from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum, auto

import agent_config as config
from llm.factory import build_adapter_with_fallback as build_adapter
from llm.prompts import build_system_prompt
from memory import session as session_store
from tools import registry
from tools.orchestrator import (
    ToolOrchestrator,
    get_pending_tool,
    is_confirmation_message,
    mark_confirmed,
)
from tools.registry import ToolResult

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8


class _State(Enum):
    THINKING        = auto()
    EXECUTING       = auto()
    WAITING_CONFIRM = auto()
    RESPONDING      = auto()


def _tool_result_content(result: ToolResult, tc_name: str) -> str:
    """Serializa ToolResult para el mensaje 'tool' que ve el LLM."""
    if result.success:
        raw = result.raw if result.raw is not None else ""
        payload = {"output": raw}
        if result.verified:
            payload["verified"] = True
    else:
        payload = {
            "success": False,
            "error": result.error or "error desconocido",
        }
        if result.blocked:
            payload["blocked"] = True
    return json.dumps(payload, ensure_ascii=False)


async def process_message(
    message: str,
    session_id: str | None,
    user_id: str = "default",
    model_ref: str | None = None,
) -> dict:
    """Procesa un mensaje de usuario y retorna la respuesta del agente."""

    if not session_id:
        session_id = await session_store.create_session(user_id)

    # ── Flujo de confirmación ─────────────────────────────────────────────────
    # Si el usuario confirma, el runtime re-ejecuta la ToolCall preservada
    # directamente — no se le pide al LLM que "recuerde" qué tenía que hacer.
    if is_confirmation_message(message):
        pending = get_pending_tool(session_id)
        if pending:
            confirmed_tc = mark_confirmed(session_id)
            await session_store.add_message(session_id, "user", message)
            return await _resume_after_confirm(session_id, model_ref, confirmed_tc)

    # ── Flujo normal ──────────────────────────────────────────────────────────
    history = (await session_store.get_history(session_id))[-20:]
    await session_store.add_message(session_id, "user", message)

    system   = build_system_prompt()
    messages = list(history) + [{"role": "user", "content": message}]
    return await _run_fsm(session_id, messages, system, model_ref)


async def _resume_after_confirm(
    session_id: str,
    model_ref: str | None,
    confirmed_tc,
) -> dict:
    """Re-ejecuta la ToolCall confirmada y continúa el loop desde ese punto."""
    history  = (await session_store.get_history(session_id))[-20:]
    system   = build_system_prompt()
    messages = list(history)

    orchestrator = ToolOrchestrator(session_id)
    result = await orchestrator.execute(confirmed_tc)

    messages.append({
        "role": "tool",
        "tool_call_id": confirmed_tc.id,
        "name": confirmed_tc.name,
        "content": _tool_result_content(result, confirmed_tc.name),
    })

    if not result.success:
        reply = await _force_error_report(messages, system, model_ref, [confirmed_tc.name])
        await session_store.add_message(session_id, "assistant", reply, [confirmed_tc.name], 0)
        return _make_response(session_id, reply, [confirmed_tc.name], 0, 0)

    return await _run_fsm(session_id, messages, system, model_ref,
                          tools_used=[confirmed_tc.name])


async def _run_fsm(
    session_id: str,
    messages: list[dict],
    system: str,
    model_ref: str | None,
    tools_used: list[str] | None = None,
) -> dict:
    """Loop FSM principal: THINKING → EXECUTING → RESPONDING."""
    tools_cfg    = config.get("tools", {}) or {}
    llm_tools    = registry.tools_for_llm(
        tools_cfg.get("allow", ["*"]), tools_cfg.get("deny", [])
    )
    adapter      = build_adapter(model_ref)
    orchestrator = ToolOrchestrator(session_id)
    used         = list(tools_used or [])
    response     = None
    error_msg    = None
    state        = _State.THINKING

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            # ── THINKING ─────────────────────────────────────────────────────
            state    = _State.THINKING
            response = await adapter.chat(messages, tools=llm_tools or None, system=system)

            if not response.has_tool_calls:
                state = _State.RESPONDING
                break

            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ],
            })

            # ── EXECUTING ────────────────────────────────────────────────────
            state        = _State.EXECUTING
            any_failed   = False
            any_blocked  = False
            failed_names = []

            for tc in response.tool_calls:
                used.append(tc.name)
                result = await orchestrator.execute(tc)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.name,
                    "content": _tool_result_content(result, tc.name),
                })

                if result.blocked:
                    any_blocked = True
                    failed_names.append(tc.name)
                    break

                if not result.success:
                    any_failed = True
                    failed_names.append(tc.name)
                    break

            # ── Decisión post-ejecución ───────────────────────────────────────
            if any_blocked:
                pending = get_pending_tool(session_id)
                if pending:
                    state = _State.WAITING_CONFIRM
                    confirm_msg = (
                        f"⚠️ La acción **{pending.name}** requiere tu confirmación.\n"
                        f"Argumentos: `{json.dumps(pending.arguments, ensure_ascii=False)[:300]}`\n\n"
                        "Escribe **confirmar** para proceder o cualquier otra cosa para cancelar."
                    )
                    await session_store.add_message(session_id, "assistant", confirm_msg, used, 0)
                    return _make_response(session_id, confirm_msg, used,
                                         response.output_tokens if response else 0,
                                         response.input_tokens if response else 0,
                                         needs_confirm=True)
                break

            if any_failed:
                reply = await _force_error_report(messages, system, model_ref, failed_names)
                await session_store.add_message(session_id, "assistant", reply, used, 0)
                return _make_response(session_id, reply, used, 0, 0)

        # ── RESPONDING ───────────────────────────────────────────────────────
        if response and response.has_tool_calls and state != _State.RESPONDING:
            messages.append({
                "role": "user",
                "content": "Resume en texto todo lo que realizaste y concluye tu respuesta.",
            })
            response = await adapter.chat(messages, tools=None, system=system)

        if response and not response.content:
            messages.append({
                "role": "user",
                "content": "Tu respuesta estaba vacía. Responde en texto con lo que encontraste o hiciste.",
            })
            response = await adapter.chat(messages, tools=None, system=system)

    except Exception as exc:
        log.error("LLM error: %s", exc, exc_info=True)
        error_msg = f"⚠️ Error del proveedor LLM: {type(exc).__name__}: {exc}"

    final = error_msg or (response.content if response else "")
    await session_store.add_message(
        session_id, "assistant", final, used,
        response.output_tokens if response else 0,
    )
    return _make_response(
        session_id, final, used,
        response.output_tokens if response else 0,
        response.input_tokens if response else 0,
    )


async def _force_error_report(
    messages: list[dict],
    system: str,
    model_ref: str | None,
    failed_names: list[str],
) -> str:
    adapter  = build_adapter(model_ref)
    messages = list(messages) + [{
        "role": "user",
        "content": (
            f"Las herramientas {', '.join(failed_names)} fallaron. "
            "Reporta exactamente el error que recibiste al usuario. "
            "No inventes resultados ni digas que funcionó."
        ),
    }]
    try:
        r = await adapter.chat(messages, tools=None, system=system)
        return r.content or f"Las herramientas {', '.join(failed_names)} fallaron."
    except Exception:
        return f"Las herramientas {', '.join(failed_names)} fallaron y no se pudo generar un reporte."


def _make_response(
    session_id: str,
    reply: str,
    tools_used: list[str],
    output_tokens: int,
    input_tokens: int,
    needs_confirm: bool = False,
) -> dict:
    llm_cfg = config.get("llm", {}) or {}
    result  = {
        "session_id":     session_id,
        "reply":          reply,
        "tools_used":     tools_used,
        "tokens_used":    output_tokens,
        "context_tokens": input_tokens,
        "context_limit":  int(llm_cfg.get("num_ctx", 8192)),
    }
    if needs_confirm:
        result["needs_confirm"] = True
    return result
