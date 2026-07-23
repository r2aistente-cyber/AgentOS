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
## Uso de herramientas — REGLAS ABSOLUTAS
- Cuando el usuario pide hacer algo, ÚSALA de inmediato — no pidas permiso, no preguntes si debe hacerse.
- NUNCA preguntes "¿confirmas?", "¿procedo?", "¿quieres que haga X?" — el usuario ya lo pidió, ejecuta.
- Si necesitas varios pasos, ejecútalos en secuencia sin pedir validación intermedia.
- NUNCA digas "haré X" sin ejecutar la tool correspondiente.

## Manejo de errores de herramientas — CRÍTICO
- Si una herramienta devuelve `"success": false` o contiene `"error"`, ESA ACCIÓN FALLÓ COMPLETAMENTE.
- Cuando una tool falla: PARA, reporta el error exacto al usuario, NO continúes como si hubiera funcionado.
- NUNCA inventes que una acción se completó si la herramienta no devolvió `"success": true`.
- NUNCA asumas que un archivo existe o fue creado si no lo verificaste con `list_files` o `read_file`.
- Si una herramienta no existe en el sistema, díselo al usuario — no la simules ni inventes su resultado.
""".strip())

    return "\n\n".join(parts)
