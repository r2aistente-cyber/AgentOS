"""Construye el system prompt desde la personalidad del config del agente."""
from __future__ import annotations

import agent_config as config


def build_system_prompt() -> str:
    base = config.get("system_prompt") or "Eres un asistente útil."
    personality = config.get("personality", {}) or {}
    parts = [base]

    # Identidad del agente: nombre + descripción/propósito de su config.
    # (Antes se ignoraba agent.description, así que el agente no "sabía" su fin.)
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
    empathy = personality.get("empathy")
    if empathy:
        parts.append(f"Empatía: {empathy}.")
    return "\n\n".join(parts)
