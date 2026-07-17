"""FastAPI entry point — R2 Autonomous (puerto 8234)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import backend.config as config
from backend.memory.db import init_db
from backend.memory import session as session_store

# Registrar todas las tools al arrancar
import backend.tools.base_tools.file_tools    # noqa: F401
import backend.tools.base_tools.web_tools     # noqa: F401
import backend.tools.base_tools.memory_tools  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="R2 Autonomous", version="1.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "xavier"
    specialty_id: str = "core"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tools_used: list[str] = []
    tokens: int = 0


# ─── Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    from backend.api.chat import process_message
    result = await process_message(
        message=req.message,
        session_id=req.session_id,
        user_id=req.user_id,
        specialty_id=req.specialty_id,
    )
    return ChatResponse(**result)


@app.get("/api/v1/sessions")
async def list_sessions(user_id: str = "xavier"):
    return await session_store.list_sessions(user_id)


@app.post("/api/v1/sessions/new")
async def new_session(user_id: str = "xavier", specialty_id: str = "core"):
    sid = await session_store.create_session(user_id, specialty_id)
    return {"session_id": sid}


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    s = await session_store.get_session(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    history = await session_store.get_history(session_id, limit=100)
    return {"session": s, "messages": history}


@app.delete("/api/v1/sessions/{session_id}")
async def archive_session(session_id: str):
    await session_store.archive_session(session_id)
    return {"ok": True}


@app.get("/api/v1/models")
async def list_models():
    import httpx
    host = config.get("llm.host", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{host}/api/tags")
            return r.json()
    except Exception as e:
        raise HTTPException(503, f"Ollama no disponible: {e}")


@app.get("/health")
async def health():
    from backend.llm.ollama import OllamaAdapter
    ok = await OllamaAdapter().ping()
    return {"status": "ok" if ok else "degraded", "llm": ok}


if __name__ == "__main__":
    import uvicorn
    port = config.get("server.port", 8234)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
