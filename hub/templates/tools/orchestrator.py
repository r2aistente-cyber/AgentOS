"""Ejecuta tool calls validando permisos, confirmaciones y registrando en auditoría.

Gate de confirmación (Sprint 8):
  - Tools con requires_confirm=True requieren que la sesión tenga un token de
    confirmación activo antes de ejecutarse.
  - El engine expone el token pendiente al frontend, que muestra un botón.
  - El frontend manda el mensaje de confirmación → el engine lo reconoce y activa
    el token → el LLM reintenta la tool call → se ejecuta.
"""
from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

import agent_config as config
from llm.adapter import ToolCall
from security.audit import AuditLog
from security.permissions import PermissionEnforcer
from tools import registry

# Token de confirmación por sesión: {session_id: set_de_tools_aprobadas}
# Se limpia tras cada ejecución aprobada para no reutilizarlo.
_confirmed: dict[str, set[str]] = {}

# Palabras que el usuario puede escribir para confirmar una acción peligrosa.
_CONFIRM_WORDS = {"confirmar", "confirm", "sí", "si", "yes", "ok", "adelante", "procede"}

_SECURITY_LEVEL = int((config.get("security", {}) or {}).get("level", 1))
_REQUIRE_CONFIRM_LEVEL = 2  # a partir de nivel 2 se activa el gate


def mark_confirmed(session_id: str, tool_name: str) -> None:
    """Llamado por el engine cuando detecta una palabra de confirmación del usuario."""
    _confirmed.setdefault(session_id, set()).add(tool_name)


def is_confirmation_message(text: str) -> bool:
    """True si el mensaje del usuario es una confirmación."""
    return text.strip().lower() in _CONFIRM_WORDS


class ToolOrchestrator:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id
        self._perms = PermissionEnforcer()
        self._audit = AuditLog()

    async def execute(self, tool_call: ToolCall) -> dict[str, Any]:
        start = time.monotonic()
        tool = registry.get(tool_call.name)

        if not tool:
            return self._fail(tool_call, f"Tool '{tool_call.name}' no existe", start)
        if not self._perms.is_allowed(tool_call.name):
            return self._fail(tool_call, f"Tool '{tool_call.name}' no permitida para este agente", start)

        # ── Gate de confirmación ───────────────────────────────────────────────
        if tool.requires_confirm and _SECURITY_LEVEL >= _REQUIRE_CONFIRM_LEVEL:
            sid = self.session_id or ""
            confirmed_tools = _confirmed.get(sid, set())
            if tool_call.name not in confirmed_tools:
                self._audit.log(
                    sid, tool_call.name, tool_call.arguments,
                    "PENDING_CONFIRM", False,
                    int((time.monotonic() - start) * 1000),
                )
                return {
                    "success": False,
                    "pending_confirmation": True,
                    "tool": tool_call.name,
                    "error": (
                        f"La acción '{tool_call.name}' requiere confirmación explícita. "
                        "Escribe 'confirmar' para proceder."
                    ),
                }
            # Confirmación consumida — eliminar para no reutilizar
            confirmed_tools.discard(tool_call.name)

        try:
            result = await _call(tool.handler, tool_call.arguments)
            ms = int((time.monotonic() - start) * 1000)
            self._audit.log(self.session_id, tool_call.name, tool_call.arguments, result, True, ms)
            return {"success": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            ms = int((time.monotonic() - start) * 1000)
            self._audit.log(self.session_id, tool_call.name, tool_call.arguments, str(exc), False, ms)
            return {"success": False, "error": str(exc)}

    def _fail(self, tool_call: ToolCall, msg: str, start: float) -> dict:
        ms = int((time.monotonic() - start) * 1000)
        self._audit.log(self.session_id, tool_call.name, tool_call.arguments, msg, False, ms)
        return {"success": False, "error": msg}


async def _call(handler, arguments: dict) -> Any:
    if inspect.iscoroutinefunction(handler):
        return await handler(**arguments)
    return handler(**arguments)
