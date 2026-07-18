"""Registro central de tools disponibles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ToolDef:
    name: str
    description: str
    category: str
    parameters: dict          # JSON Schema para el LLM
    handler: Callable
    dangerous: bool = False   # requiere confirmación (Sprint 8)


_REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> ToolDef | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolDef]:
    return list(_REGISTRY.values())


def tools_for_llm(allowed: list[str] | None = None, denied: list[str] | None = None) -> list[dict]:
    """Formato OpenAI/Ollama para el payload del LLM."""
    denied = denied or []
    out = []
    for t in _REGISTRY.values():
        if t.name in denied:
            continue
        if allowed and allowed != ["*"] and "*" not in allowed and t.name not in allowed:
            continue
        out.append({
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        })
    return out
