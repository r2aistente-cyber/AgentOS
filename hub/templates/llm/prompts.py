"""Construye el system prompt desde la personalidad del config del agente."""
from __future__ import annotations

import agent_config as config


def build_system_prompt() -> str:
    base = config.get("system_prompt") or "Eres un asistente útil."
    personality = config.get("personality", {}) or {}
    parts = [base]

    name = config.get("agent.name")
    if name:
        parts.append(f"Te llamas {name}.")
    description = config.get("agent.description")
    if description:
        parts.append(f"Tu propósito: {description}.")

    tone = personality.get("tone")
    if tone:
        parts.append(f"Tono: {tone}.")
    humor = personality.get("humor")
    if humor and humor not in ("none", "ninguno"):
        parts.append(f"Humor: {humor}.")

    parts.append("""
## Uso de herramientas
Tienes acceso a herramientas (tools) para ejecutar acciones reales. Reglas:
- Cuando el usuario pide hacer algo que requiere una herramienta, ÚSALA de inmediato — no pidas permiso, no preguntes si debe hacerse, no valides antes de ejecutar.
- NUNCA preguntes "¿quieres que haga X?", "¿confirmas?", "¿procedo?" ni ninguna variante. El usuario ya lo pidió — ejecuta.
- Ejecuta la herramienta primero, luego responde con los resultados reales obtenidos.
- Si una herramienta falla, reporta el error exacto — no inventes un resultado.
- Si necesitas varios pasos (buscar → leer → escribir), ejecuta cada uno en secuencia sin pedir validación intermedia.
- NUNCA digas "haré X" sin ejecutar la tool correspondiente.
""".strip())

    return "\n\n".join(parts)
