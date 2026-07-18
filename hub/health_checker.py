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
        self.interval = int(config.get("hub.health_check.interval_seconds", 15))
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
            # Solo vigilamos agentes que el Hub cree que están online
            if info.status != "online" or proc is None:
                continue

            alive = False
            if proc.is_alive:
                try:
                    r = await client.get(proc.health_url)
                    alive = r.status_code == 200
                except Exception:  # noqa: BLE001
                    alive = False

            if not alive:
                log.warning("Agente '%s' no responde health check", info.name)
                if info.auto_restart:
                    log.info("Auto-reiniciando '%s'", info.name)
                    try:
                        await asyncio.to_thread(self.manager.restart, info.name)
                    except Exception as e:  # noqa: BLE001
                        log.error("Fallo al reiniciar '%s': %s", info.name, e)
                else:
                    self.manager._set_status(info.name, "error")
