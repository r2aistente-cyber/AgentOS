"""Lectura de config.yaml con acceso tipado."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get(key: str, default: Any = None) -> Any:
    """Acceso puntado: get('llm.model') → 'qwen2.5:latest'"""
    parts = key.split(".")
    node = _load()
    for part in parts:
        if not isinstance(node, dict):
            return default
        node = node.get(part, default)
        if node is default:
            return default
    return node


def get_secret(name: str) -> str | None:
    """Lee un secreto del entorno o keychain. Nunca texto plano en config."""
    env_map = {
        "github_token": "GITHUB_TOKEN",
        "openai_key": "OPENAI_API_KEY",
        "anthropic_key": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(name)
    if env_var:
        return os.environ.get(env_var)
    return os.environ.get(name.upper())


def reload() -> None:
    _load.cache_clear()
