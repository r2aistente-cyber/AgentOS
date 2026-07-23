"""Construye el system prompt desde la personalidad del config del agente."""
from __future__ import annotations

import agent_config as config
from security.sandbox import Sandbox


def _workspace_block() -> str:
    """Informa al agente de su workspace y qué contiene actualmente."""
    try:
        ws = Sandbox.primary_dir()
        ws.mkdir(parents=True, exist_ok=True)
        entries = sorted(ws.iterdir())
        if entries:
            listing = "\n".join(
                f"  {'[DIR] ' if e.is_dir() else ''}{e.name}"
                for e in entries[:30]
            )
        else:
            listing = "  (vacío)"
        return (
            f"## Tu workspace\n"
            f"Ruta: `{ws}`\n"
            f"Todas las operaciones de archivos ocurren dentro de esta carpeta.\n"
            f"Usa rutas relativas (ej: `archivo.py`, `src/main.py`) — el sistema\n"
            f"las resuelve automáticamente dentro de tu workspace.\n\n"
            f"Contenido actual:\n{listing}"
        )
    except Exception:
        return ""


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

    ws_block = _workspace_block()
    if ws_block:
        parts.append(ws_block)

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
