"""Ejecuta tool calls validando permisos y registrando en auditoría."""
from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

from llm.adapter import ToolCall
from security.audit import AuditLog
from security.permissions import PermissionEnforcer
from tools import registry


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
