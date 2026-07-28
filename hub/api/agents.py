"""CRUD y ciclo de vida de agentes."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hub import config as hub_config
from hub import specialty_loader
from hub.agent_manager import AgentManager, _deep_merge
from hub.exporter import export_agent
from hub.importer import import_agent
from hub.whatsapp_manager import WhatsAppManager

_HUB_URL = "http://localhost:8234"

router = APIRouter(prefix="/api/v1/hub", tags=["agents"])

# Instancias únicas compartidas por el proceso del Hub
manager = AgentManager()
wa_manager = WhatsAppManager()


class CreateAgentRequest(BaseModel):
    name: str
    install_path: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    specialty: str | None = None  # p. ej. "r2-legal" — ver hub/specialty_loader.py


class ConfigUpdateRequest(BaseModel):
    config: dict[str, Any]


def _info(name_or_info) -> dict:
    info = name_or_info
    return info.to_dict()


@router.get("/specialties")
def list_specialties() -> list[dict]:
    """Catálogo de specialties disponibles — para el selector del wizard
    de creación de agentes (ver hub/specialty_loader.py)."""
    out = []
    for path in sorted(hub_config.specialties_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        out.append({
            "id": data.get("id", path.stem),
            "name": data.get("name", path.stem),
            "description": data.get("description", ""),
        })
    return out


@router.get("/specialties/{specialty_id}/preview")
def preview_specialty(specialty_id: str) -> dict:
    """Resuelve una specialty sin crear ningún agente — para que el wizard
    prellene campos y muestre sus skills antes de confirmar la creación."""
    try:
        resolved = specialty_loader.resolve_specialty(specialty_id)
        summary = specialty_loader.skills_summary(specialty_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "config_body": resolved["config_body"],
        "missing_knowledge_files": resolved["missing_knowledge_files"],
        **summary,
    }


@router.get("/agents")
def list_agents() -> list[dict]:
    return [a.to_dict() for a in manager.list()]


@router.post("/agents", status_code=201)
def create_agent(req: CreateAgentRequest) -> dict:
    config_body = req.config
    knowledge_files: list[Path] = []

    if req.specialty:
        try:
            resolved = specialty_loader.resolve_specialty(req.specialty)
        except FileNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e))
        # Lo explícito en req.config gana sobre lo resuelto del specialty.
        config_body = _deep_merge(resolved["config_body"], req.config)
        knowledge_files = resolved["knowledge_source_files"]

    try:
        info = manager.create(req.name, config_body, req.install_path)
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if knowledge_files:
        dest_dir = Path(info.dir) / "data" / "knowledge"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src in knowledge_files:
            shutil.copy(src, dest_dir / src.name)
        # El default de _build_agent_config apunta a workspace/knowledge/
        # (que no llega a crearse) — para agentes con specialty, corregimos
        # a la carpeta que sí existe (data/knowledge/).
        cfg = manager.get_config(req.name)
        cfg["knowledge"] = [str(dest_dir)]
        info = manager.update_config(req.name, cfg)

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


@router.post("/agents/{name}/sync")
def sync_agent(name: str) -> dict:
    """Actualiza el código del agente (engine, tools, security, memory...)
    desde hub/templates/, sin tocar config.yaml ni data/. Requiere reiniciar
    el agente después para que el código nuevo tome efecto."""
    try:
        return manager.sync_from_template(name).to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents/{name}/token")
def get_agent_token(name: str) -> dict:
    """Devuelve el Bearer token del agente para que el frontend lo use en sus requests."""
    try:
        cfg = manager.get_config(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    token = (cfg.get("security") or {}).get("token")
    if not token:
        # Agente sin token (creado antes de Sprint 8) — sin restricción de auth
        return {"token": None, "auth_required": False}
    return {"token": token, "auth_required": True}


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


@router.post("/agents/{name}/whatsapp/start")
def start_whatsapp(name: str, allowed_numbers: list[str] | None = None) -> dict:
    """Inicia el sidecar de WhatsApp para este agente."""
    try:
        info = manager.get(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    session_dir = Path(info.dir) / "whatsapp" / "session"
    wa_cfg = manager.get_config(name).get("channels", {}).get("whatsapp", {})
    numbers = allowed_numbers or []
    if not numbers and wa_cfg.get("allowed_numbers"):
        numbers = wa_cfg["allowed_numbers"]
    try:
        sc = wa_manager.start(name, info.port, session_dir, numbers)
        return {"started": True, "sidecar_port": sc.sidecar_port}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{name}/whatsapp/stop")
def stop_whatsapp(name: str) -> dict:
    """Detiene el sidecar de WhatsApp del agente."""
    wa_manager.stop(name)
    return {"stopped": True}


@router.get("/agents/{name}/whatsapp/status")
def whatsapp_status(name: str) -> dict:
    try:
        manager.get(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return wa_manager.status(name)


@router.get("/agents/{name}/whatsapp/qr")
def whatsapp_qr(name: str) -> dict:
    try:
        manager.get(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    qr_data = wa_manager.get_qr(name)
    if qr_data is None:
        raise HTTPException(status_code=404, detail="Sin QR disponible")
    return qr_data


@router.post("/agents/{name}/export")
async def export_agent_endpoint(name: str):
    """Exporta el agente como .tar.gz en ~/AgentOS/exports/ y devuelve la ruta."""
    try:
        info = manager.get(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    cfg = manager.get_config(name)
    description = (cfg.get("agent") or {}).get("description", "")
    agent_dir = Path(info.dir)

    pkg_bytes = await asyncio.to_thread(export_agent, name, agent_dir, description)

    exports_dir = hub_config.exports_dir()
    filename = f"{name}-export.tar.gz"
    out_path = exports_dir / filename
    await asyncio.to_thread(out_path.write_bytes, pkg_bytes)

    return {"path": str(out_path), "filename": filename, "size_kb": round(len(pkg_bytes) / 1024, 1)}


@router.post("/agents/import", status_code=201)
async def import_agent_endpoint(file: UploadFile):
    """Importa un agente desde un .tar.gz exportado por AgentOS."""
    if not file.filename or not file.filename.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un .tar.gz")

    pkg_bytes = await file.read()
    existing = {a.name for a in manager.list()}
    dest_base = hub_config.agents_dir()

    try:
        port = manager._next_port()
        agent_name, agent_dir, cfg = await asyncio.to_thread(
            import_agent, pkg_bytes, dest_base, port, existing
        )
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al importar: {e}")

    from hub.models import AgentInfo
    info = AgentInfo(
        name=agent_name,
        port=port,
        dir=str(agent_dir),
        install_path=str(agent_dir),
        status="offline",
        auto_restart=bool(cfg.get("auto_restart", False)),
    )
    with manager._lock:
        manager.agents[agent_name] = info
        manager._save_registry()

    return info.to_dict()


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
