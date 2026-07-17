"""FastAPI entry point — R2 Autonomous (puerto 8234)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import backend.config as config
from backend.memory.db import init_db

# Registrar todas las tools al arrancar
import backend.tools.base_tools.file_tools      # noqa: F401
import backend.tools.base_tools.web_tools       # noqa: F401
import backend.tools.base_tools.memory_tools    # noqa: F401
# Fase 1.5 — dev tools
import backend.tools.dev_tools.github_tools     # noqa: F401
import backend.tools.dev_tools.system_tools     # noqa: F401
import backend.tools.dev_tools.build_tools      # noqa: F401
# Fase 4 — comms tools
import backend.tools.comms_tools                # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Iniciar WhatsApp si está habilitado en config
    if config.get("channels.whatsapp.enabled", False):
        from backend.channels.whatsapp import whatsapp
        try:
            await whatsapp.connect()
        except Exception as e:
            import logging
            logging.getLogger("r2").warning(f"WhatsApp no pudo iniciar: {e}")
    yield
    # Cleanup
    if config.get("channels.whatsapp.enabled", False):
        from backend.channels.whatsapp import whatsapp
        await whatsapp.stop()


app = FastAPI(title="R2 Autonomous", version="1.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────

from backend.api.sessions import router as sessions_router
from backend.api.files import router as files_router
from backend.api.admin import router as admin_router
from backend.api.specialties import router as specialties_router
from backend.api.models import router as models_router
from backend.api.channels import router as channels_router

app.include_router(sessions_router)
app.include_router(files_router)
app.include_router(admin_router)
app.include_router(specialties_router)
app.include_router(models_router)
app.include_router(channels_router)


# ─── Chat (inline — es el endpoint principal) ─────────────────────────────

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


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["chat"])
async def chat(req: ChatRequest):
    from backend.api.chat import process_message
    result = await process_message(
        message=req.message,
        session_id=req.session_id,
        user_id=req.user_id,
        specialty_id=req.specialty_id,
    )
    return ChatResponse(**result)


# ─── Health ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health():
    from backend.llm.ollama import OllamaAdapter
    ok = await OllamaAdapter().ping()
    return {"status": "ok" if ok else "degraded", "llm": ok}


if __name__ == "__main__":
    import uvicorn
    port = config.get("server.port", 8234)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
