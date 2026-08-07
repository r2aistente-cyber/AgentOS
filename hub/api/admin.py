"""Config y estado general del Hub."""
from __future__ import annotations

import httpx
from fastapi import APIRouter

from hub import config
from hub.api.agents import manager
from hub.catalog import PROVIDER_CATALOGS

router = APIRouter(prefix="/api/v1/hub", tags=["admin"])

_OLLAMA_HOST = "http://localhost:11434"


def _ollama_models() -> list[str] | None:
    """Modelos ya instalados (`ollama pull`) vía GET /api/tags.

    A diferencia de los demás proveedores (catálogo fijo hardcodeado en
    hub/catalog.py), Ollama corre local y su catálogo es "lo que el usuario
    ya bajó" -- no tiene sentido hardcodearlo. Sin esto el wizard mostraba
    el selector de Ollama vacío (PROVIDER_CATALOGS["ollama"] = None) y
    obligaba a escribir el nombre del modelo a mano, con el typo/traducción
    accidental como resultado más probable (ej. "dolphin3:8b" tecleado como
    "delfín3:8b" -- nombre que Ollama ni siquiera reconoce como válido).
    Devuelve None (no una lista vacía) si Ollama no está corriendo, para
    que el frontend siga cayendo al campo de texto libre en vez de mostrar
    un dropdown vacío."""
    try:
        r = httpx.get(f"{_OLLAMA_HOST}/api/tags", timeout=2)
        r.raise_for_status()
        modelos = [m["name"] for m in r.json().get("models", [])]
        return modelos or None
    except (httpx.HTTPError, KeyError, ValueError):
        return None


@router.get("/info")
def hub_info() -> dict:
    start, end = config.port_range()
    return {
        "name": config.get("hub.name", "AgentOS"),
        "port": config.get("hub.port", 8234),
        "home": str(config.home_dir()),
        "templates_dir": str(config.templates_dir()),
        "port_range": {"start": start, "end": end},
        "agents_total": len(manager.list()),
    }


@router.get("/models")
def list_provider_models(provider: str | None = None) -> dict:
    """Catálogo de modelos disponibles por proveedor.

    Si provider=None, devuelve todos. None = campo de texto libre. Ollama
    es la excepción con catálogo fijo None: se consulta en vivo (ver
    _ollama_models) en vez de usar PROVIDER_CATALOGS.
    """
    if provider:
        models = _ollama_models() if provider == "ollama" else PROVIDER_CATALOGS.get(provider)
        return {provider: models}
    catalogs = dict(PROVIDER_CATALOGS)
    catalogs["ollama"] = _ollama_models()
    return catalogs


@router.get("/health")
def hub_health() -> dict:
    agents = manager.list()
    online = sum(1 for a in agents if a.status == "online")
    return {
        "status": "ok",
        "agents_total": len(agents),
        "agents_online": online,
        "agents": [{"name": a.name, "status": a.status, "port": a.port} for a in agents],
    }
