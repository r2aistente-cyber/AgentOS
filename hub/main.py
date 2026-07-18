"""R2 Hub / AgentOS — FastAPI entry point (puerto 8234)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hub import config
from hub.api.agents import manager, router as agents_router
from hub.api.admin import router as admin_router
from hub.api.fs import router as fs_router
from hub.health_checker import HealthChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("hub")

health_checker = HealthChecker(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Hub arrancando — %d agente(s) en el registro", len(manager.list()))
    # Reconciliar: al reiniciar el Hub, los subprocesos anteriores ya no existen
    for info in manager.list():
        if info.status in ("online", "starting"):
            info.status = "offline"
            info.pid = None
    manager._save_registry()
    health_checker.start()
    yield
    log.info("Hub apagando — deteniendo agentes activos")
    await health_checker.stop()
    manager.shutdown_all()


app = FastAPI(title="R2 Hub / AgentOS", version="2.0", lifespan=lifespan)

# CORS: en dev abierto; endurecer en Sprint 8 (auth + orígenes restringidos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents_router)
app.include_router(admin_router)
app.include_router(fs_router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {"service": "R2 Hub / AgentOS", "version": "2.0", "docs": "/docs"}


if __name__ == "__main__":
    port = int(config.get("hub.port", 8234))
    uvicorn.run("hub.main:app", host="127.0.0.1", port=port, reload=False)
