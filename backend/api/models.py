"""Endpoints de modelos Ollama."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import backend.config as config

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("")
async def list_models():
    import httpx
    host = config.get("llm.host", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{host}/api/tags")
            data = r.json()
            return [
                {"name": m["name"], "size": m.get("size", 0), "modified": m.get("modified_at")}
                for m in data.get("models", [])
            ]
    except Exception as e:
        raise HTTPException(503, f"Ollama no disponible: {e}")


@router.get("/active")
async def get_active_model():
    return {
        "provider": config.get("llm.provider"),
        "model": config.get("llm.model"),
        "host": config.get("llm.host"),
    }


class ModelSwitch(BaseModel):
    model: str


@router.post("/switch")
async def switch_model(req: ModelSwitch):
    """Cambia el modelo activo en config.yaml en tiempo real."""
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent.parent / "config.yaml"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["llm"]["model"] = req.model
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
    config.reload()
    return {"ok": True, "model": req.model}
