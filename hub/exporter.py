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

import yaml

# Directorios / archivos que NO se exportan
_EXCLUDE_NAMES = {"__pycache__", ".git", "whatsapp"}
_EXCLUDE_EXTS  = {".pyc", ".pyo"}
_EXCLUDE_DIRS  = {"logs"}           # logs son locales; se regeneran al arrancar

# Claves de config.yaml que son secretos y NUNCA deben viajar en el paquete
# exportado — quien reciba el .tar.gz no debería heredar las credenciales
# del agente original. Se reponen vía variable de entorno o se piden de
# nuevo al importar.
_SECRET_KEYS = {"api_key", "token", "brave_api_key"}


def _sanitize_config_yaml(raw: bytes) -> bytes:
    """Quita secretos en texto plano de config.yaml antes de empaquetar."""
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        # Config no parseable: no lo tocamos, pero tampoco lo bloqueamos.
        return raw

    def _strip(node):
        if isinstance(node, dict):
            for key in list(node.keys()):
                if key in _SECRET_KEYS:
                    node.pop(key)
                else:
                    _strip(node[key])
        elif isinstance(node, list):
            for item in node:
                _strip(item)

    _strip(data)
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).encode("utf-8")


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


_REQUIREMENTS = """\
fastapi>=0.115
uvicorn[standard]>=0.30
httpx>=0.27
pyyaml>=6
sentence-transformers>=3
chromadb>=0.5
duckduckgo-search>=8
psutil>=5
beautifulsoup4>=4
"""


def _make_install_bat() -> str:
    return (
        "@echo off\r\n"
        "setlocal\r\n"
        "cd /d %~dp0agent\r\n"
        "echo [AgentOS] Verificando Python...\r\n"
        "python --version >nul 2>&1\r\n"
        "if errorlevel 1 (\r\n"
        "    echo [ERROR] Python no encontrado.\r\n"
        "    echo Instala Python 3.10 o superior desde https://python.org\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        "echo [AgentOS] Instalando dependencias...\r\n"
        "python -m pip install -r ..\requirements.txt -q\r\n"
        "if errorlevel 1 (\r\n"
        "    echo [ERROR] Fallo al instalar dependencias.\r\n"
        "    pause\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        "echo [AgentOS] Leyendo configuracion...\r\n"
        "for /f %%i in ('python -c \"import yaml; c=yaml.safe_load(open('config.yaml')); print(c.get('agent',{}).get('port',9000))\"') do set PORT=%%i\r\n"
        "echo [AgentOS] Iniciando agente en puerto %PORT%...\r\n"
        "python -m uvicorn agent_main:app --host 0.0.0.0 --port %PORT%\r\n"
        "pause\r\n"
    )


def _make_install_sh() -> str:
    return (
        "#!/usr/bin/env bash\n"
        'set -e\n'
        'cd "$(dirname "$0")/agent"\n'
        'echo "[AgentOS] Verificando Python..."\n'
        'if ! command -v python3 &>/dev/null; then\n'
        '    echo "[ERROR] Python3 no encontrado. Instala Python 3.10+"\n'
        '    exit 1\n'
        'fi\n'
        'echo "[AgentOS] Instalando dependencias..."\n'
        'python3 -m pip install -r ../requirements.txt -q\n'
        'echo "[AgentOS] Leyendo configuracion..."\n'
        "PORT=$(python3 -c \"import yaml; c=yaml.safe_load(open('config.yaml')); print(c.get('agent',{}).get('port',9000))\")\n"
        'echo "[AgentOS] Iniciando agente en puerto $PORT..."\n'
        'exec python3 -m uvicorn agent_main:app --host 0.0.0.0 --port "$PORT"\n'
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

        # requirements.txt en la raíz (compartido entre install.bat y install.sh)
        _add_bytes(tar, "requirements.txt", _REQUIREMENTS.encode("utf-8"))

        # install scripts en la raíz
        _add_bytes(tar, "install.bat", _make_install_bat().encode("utf-8"))
        inst_sh = _make_install_sh().encode("utf-8")
        info_sh = tarfile.TarInfo(name="install.sh")
        info_sh.size = len(inst_sh)
        info_sh.mode = 0o755  # ejecutable
        tar.addfile(info_sh, io.BytesIO(inst_sh))

        # Contenido completo del agente bajo agent/
        for item in sorted(agent_dir.rglob("*")):
            if _should_exclude(item, agent_dir):
                continue
            rel = item.relative_to(agent_dir)
            arc_name = f"agent/{rel.as_posix()}"
            if item.is_file():
                if rel == Path("config.yaml"):
                    sanitized = _sanitize_config_yaml(item.read_bytes())
                    _add_bytes(tar, arc_name, sanitized)
                else:
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
