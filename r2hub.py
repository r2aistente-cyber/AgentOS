#!/usr/bin/env python3
"""CLI de R2 Hub / AgentOS.

Uso:
  r2hub list                    Lista los agentes instalados
  r2hub export <nombre>         Exporta un agente a <nombre>_FECHA.r2agent
  r2hub import <archivo.r2agent> Importa un agente desde un backup
  r2hub status                  Estado del Hub (requiere Hub corriendo)
  r2hub start <nombre>          Inicia un agente vía API del Hub
  r2hub stop <nombre>           Detiene un agente vía API del Hub
"""
from __future__ import annotations

import json
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

# ── Bootstrap ─────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from hub.agent_manager import AgentManager  # noqa: E402
from hub import config as hub_config         # noqa: E402

_EXCLUDE = {"__pycache__", "*.pyc", "node_modules"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hub_api(path: str, method: str = "GET", body: dict | None = None) -> dict:
    try:
        import httpx
        fn = getattr(httpx, method.lower())
        kwargs = {"timeout": 10}
        if body is not None:
            kwargs["json"] = body
        r = fn(f"http://localhost:{hub_config.get('hub.port', 8234)}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error al contactar el Hub: {e}")
        sys.exit(1)


def _filter_tar(ti: tarfile.TarInfo) -> tarfile.TarInfo | None:
    for excl in _EXCLUDE:
        if excl.startswith("*"):
            if ti.name.endswith(excl[1:]):
                return None
        elif excl in ti.name.split("/"):
            return None
    return ti


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_list() -> None:
    manager = AgentManager()
    agents = manager.list()
    if not agents:
        print("No hay agentes instalados.")
        return
    print(f"{'Nombre':<20} {'Puerto':<8} {'Estado':<10} {'Auto-restart'}")
    print("-" * 55)
    for a in agents:
        print(f"{a.name:<20} {a.port:<8} {a.status:<10} {'sí' if a.auto_restart else 'no'}")


def cmd_export(name: str) -> None:
    manager = AgentManager()
    if name not in manager.agents:
        print(f"Agente '{name}' no encontrado.")
        sys.exit(1)

    info = manager.agents[name]
    agent_dir = Path(info.dir)
    date = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = Path.cwd() / f"{name}_{date}.r2agent"

    # Incluir: config.yaml, memory.db, data/, logs/ (últimas 5000 líneas), whatsapp/session/, tools/
    INCLUDE = {"config.yaml", "memory.db", "data", "logs", "whatsapp", "tools"}

    print(f"Exportando '{name}' → {out_path.name}")
    with tarfile.open(out_path, "w:gz") as tar:
        # Metadata del agente
        meta = {
            "name": name,
            "port": info.port,
            "exported_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        import io
        meta_bytes = json.dumps(meta, indent=2).encode()
        ti = tarfile.TarInfo("r2agent_meta.json")
        ti.size = len(meta_bytes)
        tar.addfile(ti, io.BytesIO(meta_bytes))

        # Archivos del agente
        for item in agent_dir.iterdir():
            if item.name not in INCLUDE:
                continue
            if item.is_dir():
                tar.add(item, arcname=item.name, filter=_filter_tar)
            else:
                tar.add(item, arcname=item.name)

    size_kb = out_path.stat().st_size // 1024
    print(f"✓ Backup creado: {out_path.name} ({size_kb} KB)")


def cmd_import(file_path_str: str) -> None:
    file_path = Path(file_path_str)
    if not file_path.exists():
        print(f"Archivo no encontrado: {file_path}")
        sys.exit(1)

    with tarfile.open(file_path, "r:gz") as tar:
        # Leer metadata
        try:
            meta_f = tar.extractfile("r2agent_meta.json")
            meta = json.loads(meta_f.read())
        except Exception:
            print("Archivo .r2agent inválido o corrupto.")
            sys.exit(1)

        name = meta["name"]
        manager = AgentManager()

        if name in manager.agents:
            answer = input(f"El agente '{name}' ya existe. ¿Sobreescribir? [s/N]: ")
            if answer.strip().lower() != "s":
                print("Cancelado.")
                return
            manager.delete(name, archive=True)

        # Crear agente con config del backup
        with tempfile.TemporaryDirectory() as tmp:
            tar.extractall(tmp)
            tmp_path = Path(tmp)
            cfg_file = tmp_path / "config.yaml"
            if not cfg_file.exists():
                print("Error: config.yaml no encontrado en el backup.")
                sys.exit(1)

            import yaml
            with open(cfg_file) as f:
                agent_config = yaml.safe_load(f)

            info = manager.create(name, agent_config)
            agent_dir = Path(info.dir)

            # Restaurar datos
            for item in tmp_path.iterdir():
                if item.name in ("r2agent_meta.json", "config.yaml"):
                    continue
                dest = agent_dir / item.name
                if item.is_dir():
                    import shutil
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    import shutil
                    shutil.copy2(item, dest)

    print(f"✓ Agente '{name}' importado en {info.dir}")
    print(f"  Inicia con: POST http://localhost:8234/api/v1/hub/agents/{name}/start")


def cmd_status() -> None:
    data = _hub_api("/api/v1/hub/health")
    print(f"Hub en línea ✓  —  {data['agents_online']}/{data['agents_total']} agentes activos")
    for a in data.get("agents", []):
        icon = "🟢" if a["status"] == "online" else "🔴"
        print(f"  {icon} {a['name']:<20} :{a['port']}  {a['status']}")


def cmd_start(name: str) -> None:
    data = _hub_api(f"/api/v1/hub/agents/{name}/start", method="POST")
    print(f"✓ {name} → {data.get('status')}")


def cmd_stop(name: str) -> None:
    data = _hub_api(f"/api/v1/hub/agents/{name}/stop", method="POST")
    print(f"✓ {name} → {data.get('status')}")


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "list": (cmd_list, 0, "Lista los agentes instalados"),
    "export": (cmd_export, 1, "Exporta un agente: r2hub export <nombre>"),
    "import": (cmd_import, 1, "Importa un agente: r2hub import <archivo.r2agent>"),
    "status": (cmd_status, 0, "Estado del Hub (requiere Hub corriendo)"),
    "start": (cmd_start, 1, "Inicia un agente: r2hub start <nombre>"),
    "stop": (cmd_stop, 1, "Detiene un agente: r2hub stop <nombre>"),
}


def usage() -> None:
    print("Uso: python r2hub.py <comando> [args]")
    print()
    print("Comandos:")
    for cmd, (_, _, desc) in COMMANDS.items():
        print(f"  {cmd:<12} {desc}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        usage()
        sys.exit(0)

    cmd = args[0]
    if cmd not in COMMANDS:
        print(f"Comando desconocido: '{cmd}'")
        usage()
        sys.exit(1)

    fn, nargs, _ = COMMANDS[cmd]
    if len(args) - 1 < nargs:
        print(f"Error: '{cmd}' requiere {nargs} argumento(s)")
        sys.exit(1)

    fn(*args[1:nargs + 1])
