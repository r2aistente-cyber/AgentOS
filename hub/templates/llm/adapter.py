"""Interfaz abstracta para cualquier proveedor LLM.

Formato interno de mensajes = estilo OpenAI/Ollama (role/content + tool_calls +
role:"tool" con tool_call_id). Ollama y OpenAI lo usan nativo; el adapter de
Anthropic traduce a/desde el formato de Claude.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMAdapter(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Envía mensajes al LLM y devuelve la respuesta."""

    @abstractmethod
    async def ping(self) -> bool:
        """Verifica que el proveedor responde."""
