"""Tools Git — operaciones de lectura sobre repositorios."""
from __future__ import annotations

import asyncio
from pathlib import Path

from tools.registry import ToolDef, register


async def _git(args: list[str], cwd: str | None = None, timeout: int = 15) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()[:4000]
    except asyncio.TimeoutError:
        return "[TIMEOUT] git tardó demasiado"
    except FileNotFoundError:
        return "[ERROR] git no está instalado o no está en el PATH"
    except Exception as e:
        return f"[ERROR] {e}"


async def git_status(path: str = ".") -> str:
    """Estado del working tree de un repositorio git."""
    return await _git(["status", "--short", "--branch"], cwd=path)


async def git_log(path: str = ".", n: int = 10) -> str:
    """Últimos N commits del repositorio."""
    return await _git(["log", f"--oneline", f"-{n}"], cwd=path)


async def git_diff(path: str = ".", staged: bool = False) -> str:
    """Diff del working tree (o staged si staged=True)."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    args += ["--stat", "--patch", "--no-color"]
    return await _git(args, cwd=path)


async def git_show(ref: str = "HEAD", path: str = ".") -> str:
    """Muestra el contenido de un commit específico."""
    return await _git(["show", "--no-color", ref], cwd=path)


register(ToolDef(
    name="git_status",
    description="Muestra el estado del working tree de un repo git (rama, archivos modificados).",
    category="git",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta al repositorio", "default": "."}},
        "required": [],
    },
    handler=git_status,
))

register(ToolDef(
    name="git_log",
    description="Muestra los últimos N commits del repositorio.",
    category="git",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta al repositorio", "default": "."},
            "n": {"type": "integer", "description": "Número de commits a mostrar", "default": 10},
        },
        "required": [],
    },
    handler=git_log,
))

register(ToolDef(
    name="git_diff",
    description="Muestra el diff del working tree o staged changes.",
    category="git",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta al repositorio", "default": "."},
            "staged": {"type": "boolean", "description": "Ver cambios en staging (git diff --staged)", "default": False},
        },
        "required": [],
    },
    handler=git_diff,
))

register(ToolDef(
    name="git_show",
    description="Muestra el contenido de un commit (por defecto HEAD).",
    category="git",
    parameters={
        "type": "object",
        "properties": {
            "ref": {"type": "string", "description": "Referencia del commit (hash, rama, HEAD)", "default": "HEAD"},
            "path": {"type": "string", "description": "Ruta al repositorio", "default": "."},
        },
        "required": [],
    },
    handler=git_show,
))
