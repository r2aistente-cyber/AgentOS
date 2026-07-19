"""Config y estado general del Hub."""
from __future__ import annotations

from fastapi import APIRouter

from hub import config
from hub.api.agents import manager
from hub.catalog import PROVIDER_CATALOGS

router = APIRouter(prefix="/api/v1/hub", tags=["admin"])


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

    Si provider=None, devuelve todos. None = campo de texto libre.
    """
    if provider:
        models = PROVIDER_CATALOGS.get(provider)
        return {provider: models}
    return PROVIDER_CATALOGS


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
