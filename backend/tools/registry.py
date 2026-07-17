"""Registro central de herramientas disponibles."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDef:
    name: str
    description: str
    category: str
    min_level: int
    parameters: dict        # JSON Schema para el LLM
    handler: Callable
    requires_confirmation: bool = False


_REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> ToolDef | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolDef]:
    return list(_REGISTRY.values())


def tools_for_llm(allowed: list[str] | None = None) -> list[dict]:
    """Genera la lista en formato Ollama/OpenAI para el payload."""
    tools = []
    for t in _REGISTRY.values():
        if allowed and allowed != ["*"] and t.name not in allowed:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        })
    return tools
