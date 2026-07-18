"""CRUD y ciclo de vida de agentes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from hub.agent_manager import AgentManager

router = APIRouter(prefix="/api/v1/hub", tags=["agents"])

# Instancia única del gestor (compartida por el proceso del Hub)
manager = AgentManager()


class CreateAgentRequest(BaseModel):
    name: str
    install_path: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ConfigUpdateRequest(BaseModel):
    config: dict[str, Any]


def _info(name_or_info) -> dict:
    info = name_or_info
    return info.to_dict()


@router.get("/agents")
def list_agents() -> list[dict]:
    return [a.to_dict() for a in manager.list()]


@router.post("/agents", status_code=201)
def create_agent(req: CreateAgentRequest) -> dict:
    try:
        info = manager.create(req.name, req.config, req.install_path)
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return info.to_dict()


@router.get("/agents/{name}")
def get_agent(name: str) -> dict:
    try:
        return manager.get(name).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/agents/{name}")
def delete_agent(name: str, archive: bool = True) -> dict:
    try:
        manager.delete(name, archive=archive)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"deleted": name, "archived": archive}


@router.post("/agents/{name}/start")
def start_agent(name: str) -> dict:
    try:
        return manager.start(name).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{name}/stop")
def stop_agent(name: str) -> dict:
    try:
        return manager.stop(name).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/agents/{name}/restart")
def restart_agent(name: str) -> dict:
    try:
        return manager.restart(name).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (TimeoutError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{name}/config")
def get_agent_config(name: str) -> dict:
    try:
        return manager.get_config(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/agents/{name}/config")
def update_agent_config(name: str, req: ConfigUpdateRequest) -> dict:
    try:
        return manager.update_config(name, req.config).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
