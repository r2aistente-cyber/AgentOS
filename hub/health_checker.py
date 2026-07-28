"""Health checker — verifica agentes periódicamente y auto-reinicia si procede."""
from __future__ import annotations

import asyncio
import logging

import httpx

from hub import config
from hub.agent_manager import AgentManager

log = logging.getLogger("hub.health")


class HealthChecker:
    def __init__(self, manager: AgentManager):
        self.manager = manager
        self.interval = int(config.get("hub.health_check.interval_seconds", 10))
        self.timeout = float(config.get("hub.health_check.timeout_seconds", 5))
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _loop(self) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while not self._stop.is_set():
                await self._check_all(client)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
                except asyncio.TimeoutError:
                    pass

    async def _check_all(self, client: httpx.AsyncClient) -> None:
        for info in self.manager.list():
            proc = self.manager.processes.get(info.name)
            # "error" también se revisa (no solo online/starting): un
            # timeout transitorio (ej. el agente bloqueado un momento
            # cargando el modelo de embeddings del RAG en el primer mensaje)
            # marcaba el agente como "error" para siempre — sin esto, nunca
            # se volvía a chequear aunque el proceso siguiera sano y
            # respondiendo bien un momento después.
            if info.status not in ("online", "starting", "error") or proc is None:
                continue

            # Detección inmediata: si el proceso OS ya murió, actuar sin esperar timeout HTTP
            if not proc.is_alive:
                if info.status != "error":
                    log.warning("Proceso del agente '%s' murió (PID=%s)", info.name, proc.pid)
                    await self._handle_down(info.name, proc)
                continue

            # Proceso vivo → verificar health endpoint
            alive = False
            try:
                r = await client.get(proc.health_url)
                alive = r.status_code == 200
            except Exception:
                alive = False

            if alive:
                if info.status == "error":
                    log.info("Agente '%s' volvió a responder — recuperando estado 'online'", info.name)
                    self.manager._set_status(info.name, "online")
            elif info.status != "error":
                log.warning("Agente '%s' no responde en %s", info.name, proc.health_url)
                await self._handle_down(info.name, proc)

    async def _handle_down(self, name: str, proc) -> None:
        info = self.manager.agents.get(name)
        if info is None:
            return
        if info.auto_restart:
            log.info("Auto-reiniciando '%s'", name)
            try:
                await asyncio.to_thread(self.manager.restart, name)
                log.info("'%s' reiniciado correctamente", name)
            except Exception as e:
                log.error("Fallo al reiniciar '%s': %s", name, e)
                self.manager._set_status(name, "error")
        else:
            self.manager._set_status(name, "error")
