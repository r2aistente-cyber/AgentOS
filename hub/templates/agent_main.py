"""Engine base de un agente — STUB (Sprint 1).

Cada agente recibe UNA COPIA de este archivo en su propio directorio y se lanza
con:  uvicorn agent_main:app --port <port> --host 127.0.0.1  (cwd = dir del agente)

En Sprint 1 solo expone health check + un /chat de eco. El LLM, tools y memoria
reales llegan en Sprint 2 (se copiarán llm/, tools/, security/, memory/ aquí).
"""
from __future__ import annotations

import time
from pathlib import Path

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

AGENT_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = AGENT_DIR / "config.yaml"
CONFIG = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) if _CONFIG_PATH.exists() else {}

AGENT_NAME = CONFIG.get("agent", {}).get("name", AGENT_DIR.name)
MODEL = CONFIG.get("llm", {}).get("model", "unknown")

app = FastAPI(title=f"Agent: {AGENT_NAME}", version="0.1-stub")
_START = time.time()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default"


@app.get("/api/v1/health")
def health() -> dict:
    data_dir = AGENT_DIR / "data"
    files_count = len(list(data_dir.glob("*"))) if data_dir.exists() else 0
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "model": MODEL,
        "uptime": round(time.time() - _START, 1),
        "files_count": files_count,
        "sessions_active": 0,
        "stub": True,
    }


@app.post("/api/v1/chat/simple")
@app.post("/api/v1/chat")
def chat(req: ChatRequest) -> dict:
    # STUB: eco hasta que el engine real (Sprint 2) lo reemplace
    return {
        "session_id": req.session_id or "stub-session",
        "reply": f"[{AGENT_NAME} · stub] recibí: {req.message}",
        "tools_used": [],
        "tokens_used": 0,
    }
