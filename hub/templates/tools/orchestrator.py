"""Ejecuta tool calls con verificación en código — estilo OpenClaw.

Principios:
  - El runtime verifica pre y postcondiciones, no el LLM.
  - Hooks before_tool / after_tool interceptan cada ejecución.
  - ToolResult.success lo determina el código, nunca el modelo.
  - Confirmaciones preservan la ToolCall completa (argumentos incluidos).
"""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable

import agent_config as config
from llm.adapter import ToolCall
from security.audit import AuditLog
from security.permissions import PermissionEnforcer
from tools import registry
from tools.registry import ToolResult

log = logging.getLogger(__name__)

# ── Gate de confirmación ──────────────────────────────────────────────────────
# Preserva la ToolCall COMPLETA (no solo el nombre) para reinyectarla
# directamente sin pasar por el LLM tras la confirmación del usuario.
_pending:   dict[str, ToolCall]   = {}   # session_id → ToolCall pendiente
_confirmed: dict[str, set[str]]   = {}   # session_id → tools aprobadas

_CONFIRM_WORDS = frozenset({
    "confirmar", "confirm", "sí", "si", "yes", "ok", "adelante", "procede", "dale"
})

_SECURITY_LEVEL       = int((config.get("security", {}) or {}).get("level", 1))
_REQUIRE_CONFIRM_LEVEL = 2


def is_confirmation_message(text: str) -> bool:
    return text.strip().lower() in _CONFIRM_WORDS


def get_pending_tool(session_id: str) -> ToolCall | None:
    """Retorna la ToolCall pendiente de confirmación (argumentos completos)."""
    return _pending.get(session_id)


def mark_confirmed(session_id: str) -> ToolCall | None:
    """Consume el token y retorna la ToolCall lista para ejecutar."""
    tc = _pending.pop(session_id, None)
    if tc:
        _confirmed.setdefault(session_id, set()).add(tc.name)
    return tc


# ── Hooks del runtime (before_tool / after_tool) ─────────────────────────────
_before_hooks: list[Callable] = []
_after_hooks:  list[Callable] = []


def register_before_hook(fn: Callable) -> None:
    _before_hooks.append(fn)


def register_after_hook(fn: Callable) -> None:
    _after_hooks.append(fn)


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ToolOrchestrator:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or ""
        self._perms = PermissionEnforcer()
        self._audit = AuditLog()

    async def execute(self, tool_call: ToolCall) -> ToolResult:
        """Pipeline de ejecución verificada. El LLM nunca decide si funcionó."""
        start = time.monotonic()
        sid   = self.session_id
        name  = tool_call.name
        args  = tool_call.arguments

        # 1. ¿Existe la tool?
        tool = registry.get(name)
        if not tool:
            return self._fail(name, args,
                f"Tool '{name}' no existe en este agente. "
                "Solo puedes usar las tools listadas en tu configuración.",
                start, blocked=True)

        # 2. ¿Está permitida para este agente?
        if not self._perms.is_allowed(name):
            return self._fail(name, args,
                f"Tool '{name}' no está en la lista de tools permitidas.",
                start, blocked=True)

        # 3. Gate de confirmación (decisión del runtime, no del LLM)
        if tool.requires_confirm and _SECURITY_LEVEL >= _REQUIRE_CONFIRM_LEVEL:
            confirmed_set = _confirmed.get(sid, set())
            if name not in confirmed_set:
                _pending[sid] = tool_call          # guardar COMPLETA con args
                self._audit.log(sid, name, args, "PENDING_CONFIRM", False,
                                int((time.monotonic() - start) * 1000))
                return ToolResult(
                    raw=None, success=False, blocked=True,
                    error=(f"'{name}' requiere confirmación explícita. "
                           "Escribe 'confirmar' para proceder."),
                )
            confirmed_set.discard(name)

        # 4. Hooks before_tool (el hook puede bloquear con {"block": True})
        for hook in _before_hooks:
            try:
                verdict = await _call_maybe_async(hook, name, args)
                if isinstance(verdict, dict) and verdict.get("block"):
                    reason = verdict.get("reason", "bloqueado por hook")
                    return self._fail(name, args, reason, start, blocked=True)
            except Exception as e:
                log.warning("before_tool hook error (%s): %s", name, e)

        # 5. Precondición del contrato (código puro)
        if tool.contract and tool.contract.precondition:
            try:
                ok, reason = tool.contract.precondition(args)
                if not ok:
                    return self._fail(name, args,
                        f"Precondición no cumplida: {reason}", start)
            except Exception as e:
                return self._fail(name, args, f"Error en precondición: {e}", start)

        # 6. Ejecutar el handler
        try:
            raw = await _call(tool.handler, args)
        except Exception as exc:
            ms = int((time.monotonic() - start) * 1000)
            self._audit.log(sid, name, args, str(exc), False, ms)
            return ToolResult(raw=None, success=False, error=str(exc))

        # 7. Postcondición del contrato (el runtime verifica, no el LLM)
        verified = False
        if tool.contract and tool.contract.postcondition:
            try:
                ok, reason = tool.contract.postcondition(args, raw)
                verified = True
                if not ok:
                    ms = int((time.monotonic() - start) * 1000)
                    self._audit.log(sid, name, args, f"POSTCOND_FAIL:{reason}", False, ms)
                    return ToolResult(raw=raw, success=False, verified=True,
                                      error=f"Verificación falló: {reason}")
            except Exception as e:
                log.warning("postcondition error (%s): %s", name, e)

        # 8. Hooks after_tool
        for hook in _after_hooks:
            try:
                await _call_maybe_async(hook, name, args, result=raw)
            except Exception as e:
                log.warning("after_tool hook error (%s): %s", name, e)

        ms = int((time.monotonic() - start) * 1000)
        self._audit.log(sid, name, args, raw, True, ms)
        return ToolResult(raw=raw, success=True, verified=verified)

    def _fail(self, name: str, args: dict, msg: str, start: float,
              blocked: bool = False) -> ToolResult:
        ms = int((time.monotonic() - start) * 1000)
        self._audit.log(self.session_id, name, args, msg, False, ms)
        return ToolResult(raw=None, success=False, error=msg, blocked=blocked)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _call(handler: Callable, arguments: dict) -> Any:
    if inspect.iscoroutinefunction(handler):
        return await handler(**arguments)
    return await asyncio.to_thread(handler, **arguments)


async def _call_maybe_async(fn: Callable, *args, **kwargs) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    return fn(*args, **kwargs)
