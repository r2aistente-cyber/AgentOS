"""Construye el system prompt desde la personalidad del config del agente."""
from __future__ import annotations

import agent_config as config


def build_system_prompt() -> str:
    base = config.get("system_prompt") or "Eres un asistente útil."
    personality = config.get("personality", {}) or {}
    parts = [base]
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
