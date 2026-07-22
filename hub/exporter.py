"""Exporta un agente completo como paquete .tar.gz redistribuible.

El paquete incluye:
  - manifest.json        → metadatos del paquete
  - agent/               → config + engine + tools + knowledge + memory + data
  - install.bat / .sh    → scripts de instalación rápida

Al importar, el Hub reasigna puerto y regenera el token de seguridad.
"""
from __future__ import annotations

import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

# Directorios / archivos que NO se exportan
_EXCLUDE_NAMES = {"__pycache__", ".git", "whatsapp"}
_EXCLUDE_EXTS  = {".pyc", ".pyo"}
_EXCLUDE_DIRS  = {"logs"}           # logs son locales; se regeneran al arrancar


def _should_exclude(path: Path, agent_dir: Path) -> bool:
    rel = path.relative_to(agent_dir)
    parts = rel.parts
    if not parts:
        return False
    # Excluir raíz de directorios prohibidos o cualquier subdirectorio suyo
    if parts[0] in _EXCLUDE_NAMES or parts[0] in _EXCLUDE_DIRS:
        return True
    if path.name in _EXCLUDE_NAMES:
        return True
    if path.suffix in _EXCLUDE_EXTS:
        return True
    return False


def _make_install_bat(port_hint: int) -> str:
    return (
        "@echo off\r\n"
        ":: Instalador AgentOS — Windows\r\n"
        "echo Instalando agente...\r\n"
        "echo El Hub detectara el puerto automaticamente.\r\n"
        "echo Copia esta carpeta a tu directorio de agentes y usa el Hub para importarla.\r\n"
        "echo.\r\n"
        "echo Para importar desde el Hub:\r\n"
        "echo   POST http://localhost:8234/api/v1/hub/agents/import\r\n"
        "pause\r\n"
    )


def _make_install_sh(port_hint: int) -> str:
    return (
        "#!/usr/bin/env bash\n"
        "# Instalador AgentOS — Linux / macOS\n"
        "echo 'Importa este paquete desde el Hub:'\n"
        "echo '  POST http://localhost:8234/api/v1/hub/agents/import'\n"
        "echo 'O usa el botón Importar en la UI del Hub.'\n"
    )


def export_agent(agent_name: str, agent_dir: Path, description: str = "") -> bytes:
    """Genera el tar.gz en memoria y devuelve los bytes listos para servir."""
    manifest = {
        "name": agent_name,
        "version": "1.0",
        "description": description,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": "AgentOS Hub",
        "format": "agentos-v1",
    }

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        # manifest.json en la raíz
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode()
        _add_bytes(tar, "manifest.json", manifest_bytes)

        # install scripts en la raíz
        _add_bytes(tar, "install.bat", _make_install_bat(0).encode("utf-8"))
        _add_bytes(tar, "install.sh",  _make_install_sh(0).encode("utf-8"))

        # Contenido completo del agente bajo agent/
        for item in sorted(agent_dir.rglob("*")):
            if _should_exclude(item, agent_dir):
                continue
            rel = item.relative_to(agent_dir)
            arc_name = f"agent/{rel.as_posix()}"
            if item.is_file():
                tar.add(str(item), arcname=arc_name)
            elif item.is_dir():
                info = tarfile.TarInfo(name=arc_name)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)

    buf.seek(0)
    return buf.read()


def _add_bytes(tar: tarfile.TarFile, name: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=name)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
