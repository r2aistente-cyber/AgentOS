"""Ciclo de vida del subproceso de un agente (cross-platform)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

_IS_WINDOWS = os.name == "nt"


class AgentProcess:
    """Lanza y controla el proceso uvicorn de un agente."""

    def __init__(self, name: str, port: int, agent_dir: Path):
        self.name = name
        self.port = int(port)
        self.agent_dir = Path(agent_dir)
        self.process: subprocess.Popen | None = None
        self.start_time: float | None = None

    # ── Estado ───────────────────────────────────────────────────────────────

    @property
    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    @property
    def pid(self) -> int | None:
        return self.process.pid if self.is_alive else None

    @property
    def uptime(self) -> float:
        return (time.time() - self.start_time) if (self.is_alive and self.start_time) else 0.0

    @property
    def health_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v1/health"

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def start(self, wait_timeout: float = 15.0) -> None:
        """Lanza el agente como subproceso independiente y espera a que responda."""
        if self.is_alive:
            return

        logs_dir = self.agent_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(logs_dir / "agent.log", "a", encoding="utf-8")

        # Grupo de proceso independiente para poder matarlo limpio
        kwargs: dict = {}
        if _IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "agent_main:app",
                f"--port={self.port}",
                "--host=127.0.0.1",
                "--log-level=info",
            ],
            cwd=str(self.agent_dir),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        self.start_time = time.time()
        self._wait_ready(timeout=wait_timeout)

    def stop(self, timeout: float = 5.0) -> None:
        """Detiene el agente: terminate (graceful) → kill (forzado)."""
        if self.process is None:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout)
        self.process = None
        self.start_time = None

    def restart(self, wait_timeout: float = 15.0) -> None:
        self.stop()
        self.start(wait_timeout=wait_timeout)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _wait_ready(self, timeout: float) -> None:
        """Bloquea hasta que el health check responda 200 o se agote el tiempo."""
        deadline = time.time() + timeout
        last_err: str | None = None
        while time.time() < deadline:
            # Si el proceso ya murió, no tiene sentido seguir esperando
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(
                    f"El agente '{self.name}' murió al arrancar "
                    f"(exit {self.process.returncode}). Revisa logs/agent.log"
                )
            try:
                r = httpx.get(self.health_url, timeout=2.0)
                if r.status_code == 200:
                    return
                last_err = f"HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
            time.sleep(0.4)
        raise TimeoutError(
            f"El agente '{self.name}' no respondió health check en {timeout}s "
            f"(último error: {last_err})"
        )
