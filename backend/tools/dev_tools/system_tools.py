"""exec_command con whitelist estricta — solo Nivel 3."""
from __future__ import annotations

import subprocess
from pathlib import Path

from backend.security.sandbox import Sandbox
from backend.tools.registry import ToolDef, register

EXEC_WHITELIST: dict[str, list[str]] = {
    "git":    ["status", "add", "commit", "push", "pull", "log", "diff",
               "branch", "checkout", "merge", "clone", "fetch", "stash",
               "reset", "rebase", "tag", "show"],
    "node":   ["--version", "-e", "-p"],
    "npm":    ["install", "run", "test", "build", "start", "ci", "list",
               "update", "audit", "pack"],
    "npx":    ["*"],
    "python": ["-m", "--version", "-c", "-u"],
    "pip":    ["install", "list", "show", "freeze", "uninstall", "check"],
    "pytest": ["*"],
    "uvicorn":["*"],
    "ls":     ["*"], "cat": ["*"], "grep": ["*"], "find": ["*"],
    "echo":   ["*"], "head": ["*"], "tail": ["*"], "wc":  ["*"],
    "pwd":    [],    "whoami": [],  "which": ["*"], "env": [],
    "ps":     ["aux", "-ef", "-A"],
    "kill":   ["-9", "-15", "-SIGTERM"],
    "cargo":  ["build", "test", "run", "check", "fmt", "clippy"],
    "rustc":  ["--version"],
    "mkdir":  ["-p", "*"],
    "cp":     ["-r", "-a", "*"],
    "mv":     ["*"],
    "curl":   ["-s", "-o", "-L", "--version"],
}

EXEC_BLOCKED: list[str] = [
    "rm -rf", "rm -fr", "sudo", "su ", "chmod 777",
    "curl | sh", "curl|sh", "wget | sh", "wget|sh",
    "bash <(", "sh <(", "mkfs", "dd if=", "> /dev/sd",
    "format c:", ":(){:|:&};:", ">(", "eval $(", "exec(",
]


def exec_command(command: str, cwd: str = "") -> str:
    cmd_lower = command.lower()
    for blocked in EXEC_BLOCKED:
        if blocked in cmd_lower:
            return f"❌ Bloqueado: contiene '{blocked}'"

    parts = command.strip().split()
    if not parts:
        return "❌ Comando vacío"

    binary = parts[0]
    if binary not in EXEC_WHITELIST:
        return f"❌ '{binary}' no está en la whitelist. Permitidos: {sorted(EXEC_WHITELIST.keys())}"

    allowed_args = EXEC_WHITELIST[binary]
    if allowed_args != ["*"] and len(parts) > 1:
        subcommand = parts[1]
        if subcommand not in allowed_args and not subcommand.startswith("-"):
            return f"❌ '{binary} {subcommand}' no permitido. Subcomandos: {allowed_args}"

    work_dir: Path
    if cwd:
        try:
            work_dir = Sandbox.resolve(cwd)
        except PermissionError as e:
            return f"❌ {e}"
    else:
        work_dir = Path.home()

    try:
        result = subprocess.run(
            parts,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout[:4096]
        if result.stderr and result.returncode != 0:
            output += f"\n--- stderr ---\n{result.stderr[:1024]}"
        return output or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "❌ Timeout (30s)"
    except Exception as e:
        return f"❌ Error: {e}"


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="exec_command",
    description="Ejecuta un comando del sistema con whitelist estricta. Solo Nivel 3. Nunca sudo ni rm -rf.",
    category="dev",
    min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Comando a ejecutar"},
            "cwd": {"type": "string", "description": "Directorio de trabajo (opcional)", "default": ""},
        },
        "required": ["command"],
    },
    handler=exec_command,
))
