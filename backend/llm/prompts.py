"""Construye el system prompt inyectando la personalidad de la especialidad."""
from __future__ import annotations

import json
from pathlib import Path


def build_system_prompt(specialty: dict, extra_context: str = "") -> str:
    personality = specialty.get("personality", {})
    base = personality.get("system_prompt", "Eres un asistente útil.")

    parts = [base]

    tone = personality.get("tone")
    if tone:
        parts.append(f"Tono: {tone}.")

    humor = personality.get("humor")
    if humor and humor != "none":
        parts.append(f"Humor: {humor}.")

    if extra_context:
        parts.append(extra_context)

    return "\n\n".join(parts)


def load_specialty(specialty_id: str) -> dict:
    path = Path(__file__).parent.parent.parent / "specialties" / f"{specialty_id}.json"
    if not path.exists():
        path = Path(__file__).parent.parent.parent / "specialties" / "core.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
