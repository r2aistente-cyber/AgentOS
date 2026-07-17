"""Ejecuta tool calls validando permisos y registrando en auditoría."""
from __future__ import annotations

import time
from typing import Any

from backend.tools import registry
from backend.security.permissions import PermissionEnforcer
from backend.security.sandbox import Sandbox
from backend.security.audit import AuditLog
from backend.llm.adapter import ToolCall


class ToolOrchestrator:
    def __init__(self, user_id: str, level: int, session_id: str | None = None):
        self.user_id = user_id
        self.level = level
        self.session_id = session_id
        self._audit = AuditLog()

    async def execute(self, tool_call: ToolCall) -> dict[str, Any]:
        tool = registry.get(tool_call.name)
        start = time.monotonic()

        if not tool:
            return self._fail(tool_call, f"Tool '{tool_call.name}' no existe", start)

        if not PermissionEnforcer.check(tool_call.name, tool.min_level, self.level):
            return self._fail(
                tool_call,
                f"Nivel insuficiente (necesita {tool.min_level}, tienes {self.level})",
                start,
            )

        try:
            result = await _call(tool.handler, tool_call.arguments)
            ms = int((time.monotonic() - start) * 1000)
            self._audit.log(self.user_id, self.session_id, tool_call.name, tool_call.arguments, result, True, ms)
            return {"success": True, "result": result}
        except Exception as exc:
            ms = int((time.monotonic() - start) * 1000)
            self._audit.log(self.user_id, self.session_id, tool_call.name, tool_call.arguments, str(exc), False, ms)
            return {"success": False, "error": str(exc)}

    def _fail(self, tool_call: ToolCall, msg: str, start: float) -> dict:
        ms = int((time.monotonic() - start) * 1000)
        self._audit.log(self.user_id, self.session_id, tool_call.name, tool_call.arguments, msg, False, ms)
        return {"success": False, "error": msg}


async def _call(handler, arguments: dict) -> Any:
    import asyncio, inspect
    if asyncio.iscoroutinefunction(handler):
        return await handler(**arguments)
    return handler(**arguments)
