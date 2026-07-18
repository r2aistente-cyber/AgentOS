"""Configuración del Hub — lee el config.yaml de la raíz del repo.

Expande `~` y variables de entorno (`${VAR}`) en los valores string.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# config.yaml vive en la raíz del repo (un nivel arriba de hub/)
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

_ENV_RE = re.compile(r"\$\{([^}]+)\}")


def _expand(value: Any) -> Any:
    """Expande ${VAR} y ~ recursivamente en dicts/lists/strings."""
    if isinstance(value, str):
        value = _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), value)
        return os.path.expanduser(value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


@lru_cache(maxsize=1)
def _load() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    return _expand(yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {})


def get(key: str, default: Any = None) -> Any:
    """Acceso puntado: get('hub.port') → 8234."""
    node: Any = _load()
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


# ── Rutas base del Hub (bajo ~/AgentOS por defecto) ──────────────────────────

def home_dir() -> Path:
    """Directorio raíz del Hub (~/AgentOS)."""
    d = Path(os.path.expanduser("~")) / "AgentOS"
    d.mkdir(parents=True, exist_ok=True)
    return d


def registry_path() -> Path:
    return home_dir() / "agents.json"


def agents_dir() -> Path:
    """Ubicación por defecto para nuevos agentes (~/AgentOS/agents)."""
    d = home_dir() / "agents"
    d.mkdir(parents=True, exist_ok=True)
    return d


def archived_dir() -> Path:
    d = home_dir() / "archived"
    d.mkdir(parents=True, exist_ok=True)
    return d


def templates_dir() -> Path:
    """Origen de las plantillas de agente (hub/templates del repo)."""
    return Path(__file__).resolve().parent / "templates"


def port_range() -> tuple[int, int]:
    return (int(get("hub.port_range.start", 9000)), int(get("hub.port_range.end", 9999)))


def reload() -> None:
    _load.cache_clear()
