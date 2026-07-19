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
    """Lee un secreto del entorno o config. Cada proveedor usa su propia key.

    Orden:
    1. Si el config trae llm.api_key Y es el que corresponde al proveedor, úsala.
    2. Variable de entorno mapeada (OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENCODE_API_KEY).
    """
    # Mapa de nombre secreto → env var
    env_map = {
        "openai_key": "OPENAI_API_KEY",
        "anthropic_key": "ANTHROPIC_API_KEY",
        "opencode_key": "OPENCODE_API_KEY",
        "github_token": "GITHUB_TOKEN",
    }
    # 1. Si el config trae "llm.api_key", solo usarla si corresponde al proveedor
    #    activo, para no cruzar keys entre proveedores.
    direct = get("llm.api_key")
    provider = get("llm.provider", "")
    if direct:
        # opencode y opencode-go comparten OPENCODE_API_KEY
        if name == "opencode_key" and provider in ("opencode", "opencode-go"):
            return direct
        if name == "openai_key" and provider == "openai":
            return direct
        if name == "anthropic_key" and provider == "anthropic":
            return direct
    # 2. Variable de entorno
    env_var = env_map.get(name, name.upper())
    val = os.environ.get(env_var)
    if val:
        return val
    # 3. Fallback: si el config tiene la key y no pudimos determinarlo por provider
    #    (p.ej. es un provider custom), devolverla igual.
    if direct and name in env_map:
        return direct
    return None


def reload() -> None:
    _load.cache_clear()
