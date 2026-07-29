"""Importa un paquete .tar.gz exportado por AgentOS y lo registra en el Hub.

El importador:
  1. Valida que el paquete tenga formato agentos-v1
  2. Extrae agent/ al directorio destino
  3. Reasigna puerto y regenera token de seguridad
  4. Registra el agente en el Hub (offline)
"""
from __future__ import annotations

import io
import json
import secrets
import shutil
import tarfile
from pathlib import Path
from typing import Any

import yaml


def import_agent(
    package_bytes: bytes,
    dest_base: Path,
    assign_port: int,
    existing_names: set[str],
) -> tuple[str, Path, dict[str, Any]]:
    """Importa el paquete y devuelve (name, agent_dir, config_dict).

    Args:
        package_bytes: contenido del .tar.gz
        dest_base:     directorio base donde se instalará el agente
        assign_port:   puerto libre asignado por el Hub
        existing_names: nombres de agentes ya registrados (para evitar colisiones)
    """
    buf = io.BytesIO(package_bytes)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        # 1. Validar manifest
        manifest = _read_manifest(tar)
        if manifest.get("format") != "agentos-v1":
            raise ValueError("Formato de paquete no reconocido (se esperaba agentos-v1)")

        raw_name: str = manifest.get("name", "agent-importado").strip()
        agent_name = _unique_name(raw_name, existing_names)
        agent_dir  = (dest_base / agent_name).resolve()

        if agent_dir.exists():
            raise FileExistsError(f"El directorio '{agent_dir}' ya existe")

        # 2. Extraer solo los miembros bajo agent/ — este paquete puede venir
        # de otra máquina o de un archivo subido a mano, así que un member
        # con ../ o una ruta absoluta (que al hacer agent_dir / rel
        # simplemente REEMPLAZA a agent_dir por completo, no se concatena)
        # no es hipotético, es la superficie de ataque obvia de "extraer un
        # tar de origen no confiable". Symlinks/hardlinks también se
        # rechazan: podrían apuntar fuera del directorio destino.
        agent_dir.mkdir(parents=True)
        prefix = "agent/"
        for member in tar.getmembers():
            if not member.name.startswith(prefix):
                continue
            rel = member.name[len(prefix):]
            if not rel:
                continue
            if member.issym() or member.islnk():
                raise ValueError(f"Miembro no permitido en el paquete (symlink/hardlink): {member.name}")
            dest_path = (agent_dir / rel).resolve()
            if not (dest_path == agent_dir or agent_dir in dest_path.parents):
                raise ValueError(f"Miembro fuera del directorio destino (posible path traversal): {member.name}")
            if member.isdir():
                dest_path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                f = tar.extractfile(member)
                if f:
                    dest_path.write_bytes(f.read())

    # 3. Leer config existente y actualizar campos Hub-managed
    cfg_path = agent_dir / "config.yaml"
    if cfg_path.exists():
        cfg: dict[str, Any] = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    else:
        cfg = {}

    cfg.setdefault("agent", {})
    cfg["agent"]["name"]         = agent_name
    cfg["agent"]["port"]         = assign_port
    cfg["agent"]["install_path"] = str(agent_dir)
    cfg["agent"]["status"]       = "offline"

    # Nuevo token de seguridad (cada instancia tiene el suyo)
    cfg.setdefault("security", {})
    cfg["security"]["token"] = secrets.token_hex(32)
    cfg["agent"]["workspace"] = str(agent_dir / "workspace")
    cfg["security"].setdefault("sandbox_paths", [str(agent_dir / "workspace")])

    # Actualizar knowledge paths si apuntaban al directorio original
    if "knowledge" in cfg and isinstance(cfg["knowledge"], list):
        new_knowledge = []
        for k in cfg["knowledge"]:
            p = Path(k)
            # Si el path ya no existe, reapuntar a data/knowledge del nuevo dir
            if not p.exists():
                new_knowledge.append(str(agent_dir / "data" / "knowledge"))
            else:
                new_knowledge.append(k)
        cfg["knowledge"] = new_knowledge

    # Regenerar run scripts con el nuevo puerto
    _write_run_scripts(agent_dir, assign_port)

    # Guardar config actualizado
    cfg_path.write_text(
        yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return agent_name, agent_dir, cfg


def _read_manifest(tar: tarfile.TarFile) -> dict:
    try:
        m = tar.getmember("manifest.json")
        f = tar.extractfile(m)
        return json.loads(f.read().decode()) if f else {}
    except KeyError:
        raise ValueError("El paquete no contiene manifest.json")


def _unique_name(name: str, existing: set[str]) -> str:
    if name not in existing:
        return name
    i = 2
    while f"{name}-{i}" in existing:
        i += 1
    return f"{name}-{i}"


def _write_run_scripts(agent_dir: Path, port: int) -> None:
    sh = (
        "#!/usr/bin/env bash\n"
        'cd "$(dirname "$0")"\n'
        f"exec python -m uvicorn agent_main:app --host 127.0.0.1 --port {port}\n"
    )
    bat = (
        "@echo off\r\n"
        "cd /d %~dp0\r\n"
        f"python -m uvicorn agent_main:app --host 127.0.0.1 --port {port}\r\n"
    )
    (agent_dir / "run.sh").write_text(sh, encoding="utf-8")
    (agent_dir / "run.bat").write_text(bat, encoding="utf-8")
