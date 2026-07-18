"""Permisos por agente: qué tools puede usar (allow/deny).

En vez de niveles rígidos globales (deuda del Sprint 8), cada agente declara
en su config qué tools permite. Aquí solo se verifica esa lista.
"""
from __future__ import annotations

import agent_config as config


class PermissionEnforcer:
    def __init__(self) -> None:
        tools_cfg = config.get("tools", {}) or {}
        self.allow = tools_cfg.get("allow", ["*"])
        self.deny = tools_cfg.get("deny", []) or []

    def is_allowed(self, tool_name: str) -> bool:
        if tool_name in self.deny:
            return False
        if self.allow == ["*"] or "*" in self.allow:
            return True
        return tool_name in self.allow
