"""Config del agente — lee el config.yaml de SU propio directorio.

Cada agente corre con cwd = su carpeta y este archivo vive en la raíz del agente,
así que Path(__file__).parent es el directorio del agente.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

AGENT_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = AGENT_DIR / "config.yaml"


@lru_cache(maxsize=1)
def _load() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}


def get(key: str, default: Any = None) -> Any:
    node: Any = _load()
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def get_secret(name: str) -> str | None:
    """Lee un secreto del entorno. Nunca texto plano en config.

    Orden: valor literal en config.llm.api_key → variable de entorno mapeada.
    """
    # 1. Si el config trae la key directa (para dev), úsala
    direct = get("llm.api_key")
    if direct and name in ("openai_key", "anthropic_key", "opencode_key"):
        return direct
    env_map = {
        "openai_key": "OPENAI_API_KEY",
        "anthropic_key": "ANTHROPIC_API_KEY",
        "opencode_key": "OPENCODE_API_KEY",
        "github_token": "GITHUB_TOKEN",
    }
    env_var = env_map.get(name, name.upper())
    return os.environ.get(env_var)


def reload() -> None:
    _load.cache_clear()
