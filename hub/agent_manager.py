"""AgentManager — crea, registra y gestiona agentes independientes."""
from __future__ import annotations

import json
import secrets
import shutil
import threading
from pathlib import Path
from typing import Any

import yaml

from hub import config
from hub.agent_process import AgentProcess
from hub.models import AgentInfo


class AgentManager:
    """Gestiona los agentes del sistema.

    Cada agente vive en la ubicación que el usuario eligió; el Hub mantiene un
    registro (agents.json) de dónde está cada uno y controla sus procesos.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.agents: dict[str, AgentInfo] = self._load_registry()
        self.processes: dict[str, AgentProcess] = {}

    # ── Registro (persistencia) ─────────────────────────────────────────────

    def _load_registry(self) -> dict[str, AgentInfo]:
        path = config.registry_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {k: AgentInfo.from_dict(v) for k, v in data.items()}
        return {}

    def _save_registry(self) -> None:
        path = config.registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self.agents.items()}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Puertos ──────────────────────────────────────────────────────────────

    def _next_port(self) -> int:
        start, end = config.port_range()
        used = {a.port for a in self.agents.values()}
        for port in range(start, end + 1):
            if port not in used:
                return port
        raise RuntimeError(f"No hay puertos libres en el rango {start}-{end}")

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def create(self, name: str, config_body: dict[str, Any],
               install_path: str | None = None) -> AgentInfo:
        """Crea un nuevo agente en disco y lo registra (offline)."""
        with self._lock:
            name = (name or "").strip()
            if not name:
                raise ValueError("El nombre del agente no puede estar vacío")
            if name in self.agents:
                raise FileExistsError(f"Ya existe un agente llamado '{name}'")

            base = Path(install_path).expanduser() if install_path else config.agents_dir()
            agent_dir = (base / name).resolve()
            if agent_dir.exists():
                raise FileExistsError(f"Ya existe el directorio '{agent_dir}'")

            # 1. Estructura de directorios
            for sub in ("", "data", "data/knowledge", "logs", "tools"):
                (agent_dir / sub).mkdir(parents=True, exist_ok=True)

            # 2. Puerto único
            port = self._next_port()

            # 3. config.yaml del agente (merge sobre el default de la plantilla)
            agent_config = self._build_agent_config(name, agent_dir, port, config_body)
            (agent_dir / "config.yaml").write_text(
                yaml.safe_dump(agent_config, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            # 4. Copiar el engine template completo (agent_main + paquetes)
            self._copy_engine_template(agent_dir)

            # 5. Script de arranque (conveniencia)
            self._create_run_script(agent_dir, port)

            # 6. Registrar
            info = AgentInfo(
                name=name,
                port=port,
                dir=str(agent_dir),
                install_path=str(agent_dir),
                status="offline",
                auto_restart=bool(agent_config.get("auto_restart", False)),
            )
            self.agents[name] = info
            self._save_registry()
            return info

    def delete(self, name: str, archive: bool = True) -> None:
        """Detiene y archiva (o borra) el agente."""
        with self._lock:
            info = self._require(name)
            self._stop_unlocked(name)
            src = Path(info.dir)
            if src.exists():
                if archive:
                    dest = config.archived_dir() / name
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.move(str(src), str(dest))
                else:
                    shutil.rmtree(src)
            del self.agents[name]
            self.processes.pop(name, None)
            self._save_registry()

    def list(self) -> list[AgentInfo]:
        return list(self.agents.values())

    def get(self, name: str) -> AgentInfo:
        return self._require(name)

    def get_config(self, name: str) -> dict[str, Any]:
        info = self._require(name)
        cfg_path = Path(info.dir) / "config.yaml"
        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    def update_config(self, name: str, new_config: dict[str, Any]) -> AgentInfo:
        """Actualiza el config.yaml del agente (requiere restart para aplicar)."""
        with self._lock:
            info = self._require(name)
            # Preserva campos gestionados por el Hub
            new_config.setdefault("agent", {})
            new_config["agent"]["name"] = name
            new_config["agent"]["port"] = info.port
            new_config["agent"]["install_path"] = info.install_path
            (Path(info.dir) / "config.yaml").write_text(
                yaml.safe_dump(new_config, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            info.auto_restart = bool(new_config.get("auto_restart", info.auto_restart))
            self._save_registry()
            return info

    # ── Procesos ─────────────────────────────────────────────────────────────

    def start(self, name: str) -> AgentInfo:
        with self._lock:
            info = self._require(name)
            proc = self.processes.get(name)
            if proc is None:
                proc = AgentProcess(name, info.port, Path(info.dir))
                self.processes[name] = proc
            if proc.is_alive:
                return info
            self._set_status(name, "starting")
            try:
                proc.start()
            except Exception:
                self._set_status(name, "error")
                raise
            info.pid = proc.pid
            self._set_status(name, "online")
            return info

    def stop(self, name: str) -> AgentInfo:
        with self._lock:
            return self._stop_unlocked(name)

    def restart(self, name: str) -> AgentInfo:
        self.stop(name)
        return self.start(name)

    def shutdown_all(self) -> None:
        for name in list(self.processes.keys()):
            try:
                self.stop(name)
            except Exception:  # noqa: BLE001
                pass

    def get_logs(self, name: str, tail: int = 100) -> list[str]:
        """Devuelve las últimas N líneas del log del agente."""
        info = self._require(name)
        log_path = Path(info.dir) / "logs" / "agent.log"
        if not log_path.exists():
            return []
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-tail:] if tail > 0 else lines

    def get_stats(self, name: str) -> dict:
        """Devuelve CPU% y RAM del proceso del agente (requiere psutil)."""
        info = self._require(name)
        proc = self.processes.get(name)
        if proc is None or not proc.is_alive or proc.pid is None:
            return {"cpu_percent": None, "mem_mb": None, "uptime": 0}
        try:
            import psutil
            p = psutil.Process(proc.pid)
            return {
                "cpu_percent": p.cpu_percent(interval=0.1),
                "mem_mb": round(p.memory_info().rss / 1024 / 1024, 1),
                "uptime": round(proc.uptime, 0),
            }
        except Exception:
            return {"cpu_percent": None, "mem_mb": None, "uptime": 0}

    # ── Internos ─────────────────────────────────────────────────────────────

    def _stop_unlocked(self, name: str) -> AgentInfo:
        info = self._require(name)
        proc = self.processes.get(name)
        if proc is not None:
            proc.stop()
        info.pid = None
        self._set_status(name, "offline")
        return info

    def _require(self, name: str) -> AgentInfo:
        if name not in self.agents:
            raise KeyError(f"Agente '{name}' no encontrado")
        return self.agents[name]

    def _set_status(self, name: str, status: str) -> None:
        self.agents[name].status = status
        self._save_registry()

    def _copy_engine_template(self, agent_dir: Path) -> None:
        """Copia el engine (agent_main.py, agent_config.py, engine.py y los
        paquetes llm/tools/security/memory) al directorio del agente.

        Excluye default_config.yaml (se fusiona aparte como config.yaml) y
        cualquier __pycache__.
        """
        src = config.templates_dir()
        exclude_files = {"default_config.yaml"}
        for item in src.iterdir():
            if item.name in exclude_files or item.name == "__pycache__":
                continue
            dest = agent_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                                dirs_exist_ok=True)
            else:
                shutil.copy(item, dest)

    def _create_run_script(self, agent_dir: Path, port: int) -> None:
        """Scripts de conveniencia para lanzar el agente a mano (POSIX + Windows)."""
        sh = (
            "#!/usr/bin/env bash\n"
            'cd "$(dirname "$0")"\n'
            f"exec python -m uvicorn agent_main:app --host 127.0.0.1 --port {port}\n"
        )
        (agent_dir / "run.sh").write_text(sh, encoding="utf-8")
        bat = (
            "@echo off\r\n"
            "cd /d %~dp0\r\n"
            f"python -m uvicorn agent_main:app --host 127.0.0.1 --port {port}\r\n"
        )
        (agent_dir / "run.bat").write_text(bat, encoding="utf-8")

    def _build_agent_config(self, name: str, agent_dir: Path, port: int,
                            body: dict[str, Any]) -> dict[str, Any]:
        """Combina el default de la plantilla con lo que envió el usuario."""
        default_path = config.templates_dir() / "default_config.yaml"
        base: dict[str, Any] = {}
        if default_path.exists():
            base = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}

        merged = _deep_merge(base, body or {})
        merged.setdefault("agent", {})
        merged["agent"]["name"] = name
        merged["agent"]["port"] = port
        merged["agent"]["install_path"] = str(agent_dir)
        merged["agent"]["status"] = "offline"
        # sandbox por defecto = data/ del propio agente
        merged.setdefault("security", {})
        merged["security"].setdefault("sandbox_paths", [str(agent_dir / "data")])
        # Generar token único por agente si no viene en el body
        if not merged["security"].get("token"):
            merged["security"]["token"] = secrets.token_hex(32)
        # RAG: knowledge apunta a data/knowledge/ del agente por defecto
        merged.setdefault("knowledge", [str(agent_dir / "data" / "knowledge")])
        return merged


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
