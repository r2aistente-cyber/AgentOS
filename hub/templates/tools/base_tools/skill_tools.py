"""Tool que expone el contenido de las skills on-demand de la specialty.

Ver hub/specialty_loader.py: las skills "on demand" solo se anuncian como
un índice corto (nombre + descripción) en el system_prompt — el contenido
completo se carga acá, en runtime, cuando el LLM decide que la tarea lo
necesita.
"""
from __future__ import annotations

import agent_config as config
from tools.registry import ToolDef, register


async def activar_skill(nombre: str) -> str:
    skills = config.get("skills.on_demand", {}) or {}
    skill = skills.get(nombre)
    if not skill:
        disponibles = ", ".join(skills) or "(ninguna)"
        return f"Skill '{nombre}' no existe. Disponibles: {disponibles}"
    return skill["prompt"]


register(ToolDef(
    "activar_skill",
    "Carga las instrucciones completas de una skill on-demand anunciada en el índice del prompt.",
    "meta",
    {"type": "object", "properties": {"nombre": {"type": "string"}}, "required": ["nombre"]},
    activar_skill,
))
