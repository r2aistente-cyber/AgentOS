"""Registro central de tools.

Cada tool puede declarar un ToolContract con pre/postcondiciones
verificadas en código por el orchestrator — el LLM nunca es árbitro
de si una acción funcionó.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolContract:
    """Contratos de verificación ejecutados por el runtime, no por el LLM.

    precondition(args) → (ok, motivo)   — verificación antes de ejecutar
    postcondition(args, result) → (ok, motivo) — verificación después de ejecutar
    """
    precondition: Callable[[dict], tuple[bool, str]] | None = None
    postcondition: Callable[[dict, Any], tuple[bool, str]] | None = None


@dataclass
class ToolDef:
    name: str
    description: str
    category: str
    parameters: dict          # JSON Schema para el LLM
    handler: Callable
    dangerous: bool = False
    requires_confirm: bool = False
    contract: ToolContract | None = None


@dataclass
class ToolResult:
    """Resultado verificado de la ejecución de una tool."""
    raw: Any                        # lo que devolvió el handler
    success: bool = True            # determinado por el runtime, no el LLM
    verified: bool = False          # True si se ejecutó una postcondición
    error: str | None = None        # motivo de fallo si success=False
    blocked: bool = False           # True si fue bloqueada antes de ejecutar


_REGISTRY: dict[str, ToolDef] = {}


def register(tool: ToolDef) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> ToolDef | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolDef]:
    return list(_REGISTRY.values())


def tools_for_llm(allowed: list[str] | None = None, denied: list[str] | None = None) -> list[dict]:
    """Formato OpenAI/Ollama para el payload del LLM.

    `allowed=None` (nunca lo pasa el caller actual, pero por si acaso) se
    trata como sin restricción, igual que `["*"]`. `allowed=[]` es
    DELIBERADAMENTE distinto: significa "ninguna tool" (agente sin tools,
    ej. un modelo de Ollama sin soporte de function calling) -- antes,
    `if allowed and ...` trataba la lista vacía como falsy y caía en "sin
    restricción", el resultado opuesto al que cualquiera esperaría de un
    allow-list vacío.
    """
    allowed = ["*"] if allowed is None else allowed
    denied = denied or []
    out = []
    for t in _REGISTRY.values():
        if t.name in denied:
            continue
        if "*" not in allowed and t.name not in allowed:
            continue
        out.append({
            "type": "function",
            "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
        })
    return out
