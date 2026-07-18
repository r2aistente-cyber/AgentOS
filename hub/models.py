"""Modelos de datos del Hub."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class AgentInfo:
    """Registro de un agente conocido por el Hub.

    Se serializa a JSON en agents.json, así que todos los campos son
    tipos simples (str/int). `dir` es la ruta absoluta al directorio del agente.
    """

    name: str
    port: int
    dir: str
    install_path: str
    status: str = "offline"          # offline | starting | online | error
    pid: int | None = None
    auto_restart: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentInfo":
        # Ignora claves desconocidas para tolerar cambios de esquema
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)
