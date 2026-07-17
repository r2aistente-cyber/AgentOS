"""Niveles de permiso 0-3."""
from __future__ import annotations

LEVEL_NONE = 0       # Solo conversación
LEVEL_READ = 1       # Lectura
LEVEL_WRITE = 2      # Lectura + escritura controlada
LEVEL_AUTONOMOUS = 3 # Acción autónoma (Xavier)

LEVEL_NAMES = {
    0: "Sin acceso",
    1: "Lectura",
    2: "Escritura",
    3: "Autónomo",
}


class PermissionEnforcer:
    @staticmethod
    def check(tool_name: str, tool_min_level: int, user_level: int) -> bool:
        return user_level >= tool_min_level

    @staticmethod
    def level_name(level: int) -> str:
        return LEVEL_NAMES.get(level, "Desconocido")
