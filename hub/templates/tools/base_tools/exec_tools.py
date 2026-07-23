"""Tool exec_command — ejecuta comandos del sistema con sandbox de comandos.

Protecciones:
  - Lista de binarios bloqueados (destructivos, privilegios, exfiltración)
  - Intérpretes solo permitidos sin flags de ejecución directa (-c, -e, /c, -Command)
  - Bloqueo de patrones de encadenamiento peligroso (find -exec, xargs con exec)
  - Longitud máxima del comando
  - Timeout configurable
"""
from __future__ import annotations

import asyncio
import re
import shlex

from security.sandbox import Sandbox
from tools.registry import ToolDef, register

# ── Binarios completamente bloqueados ─────────────────────────────────────────
_BLOCKED_CMDS = {
    # Destructivos / privilegios
    "rm", "rmdir", "del", "deltree", "format", "mkfs", "dd", "fdisk",
    "shutdown", "reboot", "halt", "poweroff", "init",
    "sudo", "su", "runas", "doas",
    # Exfiltración de red
    "curl", "wget", "nc", "ncat", "netcat", "socat",
    "scp", "sftp", "ftp",
    # Modificación de usuarios
    "passwd", "useradd", "userdel", "usermod", "chpasswd",
    # Ejecución remota
    "ssh", "rsh",
    # Fork bomb conocida
    ":(){:|:&};:",
}

# ── Intérpretes que admiten ejecución directa de código ───────────────────────
# Solo están bloqueados cuando van acompañados de las flags de ejecución directa.
_INTERPRETER_EXEC_FLAGS = {
    # (binario) → conjunto de flags que habilitan eval directo
    "python":      {"-c"},
    "python3":     {"-c"},
    "python3.11":  {"-c"},
    "python3.12":  {"-c"},
    "node":        {"-e", "--eval"},
    "nodejs":      {"-e", "--eval"},
    "perl":        {"-e"},
    "ruby":        {"-e"},
    "php":         {"-r"},
    "bash":        {"-c"},
    "sh":          {"-c"},
    "zsh":         {"-c"},
    "fish":        {"-c"},
    "cmd":         {"/c", "/C"},
    "cmd.exe":     {"/c", "/C"},
    "powershell":  {"-command", "-c", "-encodedcommand", "-enc"},
    "pwsh":        {"-command", "-c", "-encodedcommand", "-enc"},
}

# ── Patrones de bypass conocidos ──────────────────────────────────────────────
# Pares (regex, motivo) evaluados contra el comando completo (case-insensitive).
_BYPASS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\bfind\b.*-exec\b',      re.I), "find -exec"),
    (re.compile(r'\bxargs\b.*-[iI]\b',     re.I), "xargs exec"),
    (re.compile(r'\beval\b\s+',            re.I), "eval"),
    (re.compile(r'\bexec\b\s+',            re.I), "exec"),
    # env usado como wrapper de otro binario
    (re.compile(r'\benv\b\s+\S*(python|node|bash|sh|ruby|perl)', re.I), "env wrapping interpreter"),
    # Redirección a archivo de sistema
    (re.compile(r'>\s*/etc/',              re.I), "write to /etc"),
    (re.compile(r'>\s*/sys/',              re.I), "write to /sys"),
    (re.compile(r'>\s*[A-Za-z]:\\Windows', re.I), "write to Windows dir"),
]

_MAX_CMD_LEN = 2048


def _classify(command: str) -> str | None:
    """Devuelve el motivo de bloqueo o None si el comando es aceptable."""
    if len(command) > _MAX_CMD_LEN:
        return f"comando demasiado largo (máx {_MAX_CMD_LEN} chars)"

    # Tokenizar
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()

    if not tokens:
        return None

    # Extraer nombre del binario (quitar rutas y .exe)
    binary = tokens[0].lower().replace("\\", "/").split("/")[-1]
    binary = binary.replace(".exe", "")

    # Binarios completamente bloqueados
    if binary in _BLOCKED_CMDS:
        return f"binario bloqueado: '{binary}'"

    # Intérpretes: bloqueados solo con sus flags de ejecución directa
    if binary in _INTERPRETER_EXEC_FLAGS:
        flags_lower = {t.lower() for t in tokens[1:]}
        blocked_flags = _INTERPRETER_EXEC_FLAGS[binary] & flags_lower
        if blocked_flags:
            return f"ejecución directa de código con '{binary} {', '.join(blocked_flags)}' bloqueada"

    # Patrones de bypass en el comando completo
    for pattern, reason in _BYPASS_PATTERNS:
        if pattern.search(command):
            return f"patrón peligroso bloqueado: {reason}"

    return None


async def exec_command(command: str, timeout: int = 120) -> str:
    """Ejecuta un comando de shell y devuelve stdout+stderr (máx 4000 chars)."""
    timeout = min(timeout, 300)
    reason = _classify(command)
    if reason:
        return f"[BLOQUEADO] {reason}."

    try:
        ws = Sandbox.primary_dir()
        ws.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ws),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            # Fallo real — el runtime lo detecta, no el LLM
            prefix = f"[FAILED exit={proc.returncode}]"
            return f"{prefix}\n{output[:3900]}" if output else prefix
        return output[:4000] if output else "(sin salida, exit 0)"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return f"[TIMEOUT] El comando tardó más de {timeout}s y fue cancelado."
    except Exception as e:
        return f"[ERROR] {e}"


register(ToolDef(
    name="exec_command",
    description=(
        "Ejecuta un comando de shell y devuelve la salida. "
        "Comandos destructivos y ejecución directa de código (python -c, node -e, bash -c…) están bloqueados."
    ),
    category="system",
    dangerous=True,
    requires_confirm=True,
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando a ejecutar"},
            "timeout": {
                "type": "integer",
                "description": "Timeout en segundos (default 120, máx 300). Usa 300 para instalaciones o procesos lentos.",
                "default": 120,
            },
        },
        "required": ["command"],
    },
    handler=exec_command,
))
