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

_fmt = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
logging.basicConfig(level=logging.INFO, format=_fmt)

# Log a archivo centralizado ~/AgentOS/logs/hub.log
from hub import config as _cfg  # noqa: E402 (import dentro del módulo para evitar circular)
_hub_log_dir = _cfg.home_dir() / "logs"
_hub_log_dir.mkdir(parents=True, exist_ok=True)
_fh = logging.FileHandler(_hub_log_dir / "hub.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter(_fmt))
logging.getLogger().addHandler(_fh)

log = logging.getLogger("hub")

health_checker = HealthChecker(manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Hub arrancando — %d agente(s) en el registro", len(manager.list()))
    # Reconciliar: al reiniciar el Hub, los subprocesos anteriores ya no existen
    auto_start_names = []
    for info in manager.list():
        if info.status in ("online", "starting"):
            info.status = "offline"
            info.pid = None
        if info.auto_restart:
            auto_start_names.append(info.name)
    manager._save_registry()

    # Auto-start: arrancar agentes con auto_restart=true en background
    if auto_start_names:
        import asyncio as _asyncio

        async def _start_auto():
            await _asyncio.sleep(1)  # Espera mínima para que FastAPI termine de arrancar
            for name in auto_start_names:
                try:
                    await _asyncio.to_thread(manager.start, name)
                    log.info("Auto-start: '%s' arrancado", name)
                except Exception as e:
                    log.warning("Auto-start falló para '%s': %s", name, e)

        _asyncio.create_task(_start_auto())

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
