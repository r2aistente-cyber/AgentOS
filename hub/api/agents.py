"""CRUD y ciclo de vida de agentes."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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


@router.get("/agents/{name}/logs")
def get_agent_logs(name: str, tail: int = 100) -> dict:
    try:
        lines = manager.get_logs(name, tail=tail)
        return {"lines": lines, "count": len(lines)}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents/{name}/stats")
def get_agent_stats(name: str) -> dict:
    try:
        return manager.get_stats(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents/{name}/logs/stream")
async def stream_agent_logs(name: str, tail: int = 50):
    """SSE: transmite logs del agente en tiempo real."""
    try:
        info = manager.get(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    log_path = Path(info.dir) / "logs" / "agent.log"

    async def generate():
        # Enviar las últimas `tail` líneas como estado inicial
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-tail:]:
                yield f"data: {line}\n\n"
        else:
            yield "data: [Sin logs aún — el archivo se crea al iniciar el agente]\n\n"

        last_size = log_path.stat().st_size if log_path.exists() else 0
        keepalive = 0

        while True:
            await asyncio.sleep(0.4)
            try:
                if not log_path.exists():
                    keepalive += 1
                    if keepalive % 25 == 0:  # cada ~10s
                        yield ": keepalive\n\n"
                    continue

                current_size = log_path.stat().st_size
                if current_size > last_size:
                    with log_path.open(encoding="utf-8", errors="replace") as f:
                        f.seek(last_size)
                        new_text = f.read(current_size - last_size)
                    for line in new_text.splitlines():
                        yield f"data: {line}\n\n"
                    last_size = current_size
                    keepalive = 0
                elif current_size < last_size:
                    last_size = current_size
                else:
                    keepalive += 1
                    if keepalive % 25 == 0:
                        yield ": keepalive\n\n"
            except GeneratorExit:
                break
            except Exception:
                break

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stats")
def hub_stats() -> dict:
    """Resumen global del Hub: agentes, estado, tokens acumulados."""
    agents = manager.list()
    by_status: dict[str, int] = {}
    for a in agents:
        by_status[a.status] = by_status.get(a.status, 0) + 1
    return {
        "total": len(agents),
        "online": by_status.get("online", 0),
        "offline": by_status.get("offline", 0),
        "error": by_status.get("error", 0),
        "starting": by_status.get("starting", 0),
    }
