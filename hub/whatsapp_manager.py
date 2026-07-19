"""Gestiona sidecars de WhatsApp (Node.js) por agente."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx

from hub import config

log = logging.getLogger("hub.whatsapp")

_SIDECAR_BASE_PORT = 3100    # 3100, 3101, 3102... uno por agente
_SIDECAR_JS = config.templates_dir() / "whatsapp" / "sidecar.js"
_SIDECAR_CWD = config.templates_dir() / "whatsapp"  # para node_modules compartidos


class SidecarProcess:
    def __init__(self, name: str, sidecar_port: int, agent_port: int, session_dir: Path,
                 allowed_numbers: list[str]):
        self.name = name
        self.sidecar_port = sidecar_port
        self.agent_port = agent_port
        self.session_dir = session_dir
        self.allowed_numbers = allowed_numbers
        self._proc: subprocess.Popen | None = None
        self._log_file = None

    @property
    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    @property
    def http(self) -> str:
        return f"http://127.0.0.1:{self.sidecar_port}"

    def start(self) -> None:
        if self.is_alive:
            return
        self.session_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.session_dir.parent / "logs" / "whatsapp.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_file = open(log_path, "a", encoding="utf-8")

        env = {**os.environ,
               "WA_SIDECAR_PORT": str(self.sidecar_port),
               "WA_AGENT_PORT":   str(self.agent_port),
               "WA_AGENT_NAME":   self.name,
               "WA_SESSION_DIR":  str(self.session_dir),
               "WA_ALLOWED_NUMBERS": ",".join(self.allowed_numbers)}

        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        self._proc = subprocess.Popen(
            ["node", str(_SIDECAR_JS)],
            cwd=str(_SIDECAR_CWD),
            env=env,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        log.info("Sidecar WA '%s' arrancado (PID=%s, puerto=%s)", self.name, self._proc.pid, self.sidecar_port)

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(self._proc.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import signal
                self._proc.send_signal(signal.SIGTERM)
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        finally:
            self._proc = None
            if self._log_file:
                try:
                    self._log_file.close()
                except Exception:
                    pass


class WhatsAppManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sidecars: dict[str, SidecarProcess] = {}
        self._ports_used: set[int] = set()

    def _next_port(self) -> int:
        port = _SIDECAR_BASE_PORT
        while port in self._ports_used:
            port += 1
        self._ports_used.add(port)
        return port

    def start(self, name: str, agent_port: int, session_dir: Path,
              allowed_numbers: list[str] | None = None) -> SidecarProcess:
        with self._lock:
            if name in self._sidecars and self._sidecars[name].is_alive:
                return self._sidecars[name]
            port = self._sidecars[name].sidecar_port if name in self._sidecars else self._next_port()
            sc = SidecarProcess(name, port, agent_port, session_dir, allowed_numbers or [])
            sc.start()
            self._sidecars[name] = sc
            return sc

    def stop(self, name: str) -> None:
        with self._lock:
            sc = self._sidecars.get(name)
            if sc:
                sc.stop()
                self._ports_used.discard(sc.sidecar_port)
                del self._sidecars[name]

    def stop_all(self) -> None:
        for name in list(self._sidecars.keys()):
            try:
                self.stop(name)
            except Exception:
                pass

    def get(self, name: str) -> SidecarProcess | None:
        return self._sidecars.get(name)

    def status(self, name: str) -> dict[str, Any]:
        sc = self._sidecars.get(name)
        if sc is None or not sc.is_alive:
            return {"running": False, "ready": False, "waiting_qr": False, "error": None}
        try:
            r = httpx.get(f"{sc.http}/status", timeout=3)
            d = r.json()
            d["running"] = True
            d["sidecar_port"] = sc.sidecar_port
            return d
        except Exception as e:
            return {"running": True, "ready": False, "waiting_qr": False, "error": str(e),
                    "sidecar_port": sc.sidecar_port}

    def get_qr(self, name: str) -> dict | None:
        sc = self._sidecars.get(name)
        if sc is None or not sc.is_alive:
            return None
        try:
            r = httpx.get(f"{sc.http}/qr", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None
