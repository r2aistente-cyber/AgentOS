"""Engine base de un agente — LLM multi-proveedor + tools + memoria.

Cada agente recibe UNA COPIA de este archivo y sus paquetes (llm/, tools/,
security/, memory/). Se lanza con:
    uvicorn agent_main:app --host 127.0.0.1 --port <port>   (cwd = carpeta del agente)

Seguridad (Sprint 8):
  - Bind a 127.0.0.1 únicamente
  - CORS restringido a Hub + frontend de desarrollo
  - Bearer token (security.token en config.yaml) requerido en todas las rutas
    excepto /api/v1/health (para el health-checker del Hub sin token)
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

import agent_config as config
from memory.db import init_db
from memory import session as session_store
from security.sandbox import Sandbox
from tools import registry
import tools.base_tools  # noqa: F401  (registra las base tools)

AGENT_NAME = config.get("agent.name", config.AGENT_DIR.name)
DATA_DIR   = Sandbox.primary_dir()   # workspace del agente (relativo a su carpeta)
_START = time.time()

# ── Token de autenticación ────────────────────────────────────────────────────
_AGENT_TOKEN: str | None = (config.get("security", {}) or {}).get("token")

# Rutas que no requieren auth (el health-checker del Hub no tiene token)
_PUBLIC_PATHS = {"/api/v1/health", "/"}

# ── Orígenes permitidos para CORS ─────────────────────────────────────────────
_HUB_PORT = int((config.get("hub", {}) or {}).get("port", 8234))
_ALLOWED_ORIGINS = [
    f"http://localhost:{_HUB_PORT}",
    f"http://127.0.0.1:{_HUB_PORT}",
    "http://localhost:5173",    # Vite dev
    "http://127.0.0.1:5173",
    "http://localhost:5500",    # pywebview shell
    "http://127.0.0.1:5500",
]


class _AuthMiddleware(BaseHTTPMiddleware):
    """Valida Bearer token si la ruta no es pública."""

    async def dispatch(self, request: Request, call_next):
        # OPTIONS = CORS preflight, siempre pasa (el CORSMiddleware lo maneja)
        if not _AGENT_TOKEN or request.url.path in _PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != _AGENT_TOKEN:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticación inválido o ausente"},
            )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    await init_db()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if config.get("llm.provider") == "ollama":
        from llm.ollama import OllamaAdapter
        asyncio.create_task(OllamaAdapter().warmup())
    async def _bg_rag():
        try:
            from engine import _ensure_rag_indexed
            await asyncio.to_thread(_ensure_rag_indexed)
        except Exception:
            pass
    asyncio.create_task(_bg_rag())
    yield


app = FastAPI(title=f"Agent: {AGENT_NAME}", version="0.3", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=False,
)
app.add_middleware(_AuthMiddleware)


# ── Modelos Pydantic ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default"
    model: str | None = None  # ref "provider/model" para cambiar en caliente


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
async def health() -> dict:
    files_count = (
        len([f for f in DATA_DIR.glob("*") if f.is_file() and not f.name.endswith(".extracted.txt")])
        if DATA_DIR.exists() else 0
    )
    sessions_count = 0
    tokens_total = 0
    try:
        from memory.db import get_db
        async with get_db() as db:
            async with db.execute("SELECT COUNT(*) FROM sessions WHERE archived=0") as cur:
                row = await cur.fetchone()
                sessions_count = row[0] if row else 0
            async with db.execute("SELECT COALESCE(SUM(tokens),0) FROM messages") as cur:
                row = await cur.fetchone()
                tokens_total = row[0] if row else 0
    except Exception:
        pass

    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "provider": config.get("llm.provider", "ollama"),
        "model": config.get("llm.model", "unknown"),
        "uptime": round(time.time() - _START, 1),
        "tools": [t.name for t in registry.all_tools()],
        "files_count": files_count,
        "sessions": sessions_count,
        "tokens_total": tokens_total,
    }


@app.post("/api/v1/chat")
@app.post("/api/v1/chat/simple")
async def chat(req: ChatRequest) -> dict:
    from engine import process_message
    return await process_message(req.message, req.session_id, req.user_id, req.model)


@app.get("/api/v1/models")
async def models() -> dict:
    llm = config.get("llm", {}) or {}
    entries = llm.get("models") or []
    if not entries:
        entries = [{"provider": llm.get("provider", "ollama"), "model": llm.get("model", "")}]
    out = []
    for e in entries:
        provider = e.get("provider", "ollama")
        model = e.get("model", "")
        ref = f"{provider}/{model}"
        out.append({
            "ref": ref,
            "provider": provider,
            "model": model,
            "label": e.get("label") or model or ref,
        })
    default_ref = f"{llm.get('provider', 'ollama')}/{llm.get('model', '')}"
    return {"models": out, "default": default_ref}


@app.get("/api/v1/sessions")
async def sessions(user_id: str = "default") -> list[dict]:
    return await session_store.list_sessions(user_id)


class NewSessionRequest(BaseModel):
    title: str = "Nueva sesión"
    user_id: str = "default"


@app.post("/api/v1/sessions", status_code=201)
async def new_session(req: NewSessionRequest) -> dict:
    sid = await session_store.create_session(req.user_id, req.title)
    return {"id": sid, "title": req.title}


@app.get("/api/v1/sessions/{session_id}/messages")
async def session_messages(session_id: str) -> list[dict]:
    return await session_store.get_messages(session_id)


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    await session_store.archive_session(session_id)
    return {"archived": session_id}


@app.post("/api/v1/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dest = DATA_DIR / Path(file.filename).name
    dest.write_bytes(await file.read())

    extracted = ""
    try:
        from file_extractor import extract_text
        extracted = extract_text(dest)
        if extracted:
            (DATA_DIR / f"{dest.name}.extracted.txt").write_text(extracted, encoding="utf-8")
    except Exception:
        pass

    return {
        "filename": dest.name,
        "size": dest.stat().st_size,
        "extracted": bool(extracted),
        "preview": extracted[:200] if extracted else None,
    }


@app.get("/api/v1/files")
async def files() -> list[dict]:
    if not DATA_DIR.exists():
        return []
    return [
        {"name": f.name, "size": f.stat().st_size}
        for f in sorted(DATA_DIR.iterdir())
        if f.is_file()
    ]


if __name__ == "__main__":
    port = int(config.get("agent.port", 9000))
    uvicorn.run("agent_main:app", host="127.0.0.1", port=port, reload=False)
