"""Tool exec_command — ejecuta comandos del sistema.

Intención: dar al agente capacidad de shell limitada y auditada.
Sprint 8 endurecerá las restricciones; hoy se bloquean los casos más peligrosos.
"""
from __future__ import annotations

import asyncio
import shlex

from tools.registry import ToolDef, register

_BLOCKED = {
    "rm", "rmdir", "del", "format", "mkfs", "dd",
    "shutdown", "reboot", "halt", "poweroff",
    "sudo", "su", "runas",
    "curl", "wget",           # usar fetch_url en su lugar
    "passwd", "useradd", "userdel",
    ":(){:|:&};:",            # fork bomb
}


async def exec_command(command: str, timeout: int = 30) -> str:
    """Ejecuta un comando de shell y devuelve stdout+stderr (máx 4000 chars)."""
    # Bloqueo básico de comandos peligrosos
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    first = tokens[0].lower().split("/")[-1].split("\\")[-1].replace(".exe", "") if tokens else ""
    if first in _BLOCKED:
        return f"[BLOQUEADO] El comando '{first}' no está permitido."

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace").strip()
        return output[:4000] if output else f"(sin salida, código {proc.returncode})"
    except asyncio.TimeoutError:
        return f"[TIMEOUT] El comando tardó más de {timeout}s y fue cancelado."
    except Exception as e:
        return f"[ERROR] {e}"


register(ToolDef(
    name="exec_command",
    description="Ejecuta un comando de shell y devuelve la salida. Usar con cautela.",
    category="system",
    dangerous=True,
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando a ejecutar"},
            "timeout": {"type": "integer", "description": "Timeout en segundos (default 30)", "default": 30},
        },
        "required": ["command"],
    },
    handler=exec_command,
))
