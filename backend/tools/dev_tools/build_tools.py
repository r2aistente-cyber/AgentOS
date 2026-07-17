"""Herramientas de build: npm, pytest, uvicorn."""
from __future__ import annotations

import subprocess
from pathlib import Path

from backend.security.sandbox import Sandbox
from backend.tools.registry import ToolDef, register


def _run(cmd: list[str], cwd: str = "") -> str:
    work_dir = Sandbox.resolve(cwd) if cwd else Path.home()
    try:
        r = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace",
        )
        out = r.stdout[-4096:] if len(r.stdout) > 4096 else r.stdout
        if r.returncode != 0:
            out += f"\n--- stderr ---\n{r.stderr[-1024:]}"
        return out or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "❌ Timeout (120s)"
    except Exception as e:
        return f"❌ {e}"


def npm_install(path: str) -> str:
    return _run(["npm", "install"], path)


def npm_run(path: str, script: str) -> str:
    return _run(["npm", "run", script], path)


def npm_build(path: str) -> str:
    return _run(["npm", "run", "build"], path)


def run_pytest(path: str, args: str = "") -> str:
    cmd = ["python", "-m", "pytest", "-v"]
    if args:
        cmd += args.split()
    return _run(cmd, path)


def run_tests(path: str) -> str:
    return run_pytest(path)


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="npm_install",
    description="Ejecuta npm install en un directorio.",
    category="dev", min_level=3,
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directorio del proyecto"}},
        "required": ["path"],
    },
    handler=npm_install,
))

register(ToolDef(
    name="npm_build",
    description="Ejecuta npm run build en un directorio frontend.",
    category="dev", min_level=3,
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=npm_build,
))

register(ToolDef(
    name="npm_run",
    description="Ejecuta un script npm (npm run <script>) en un directorio.",
    category="dev", min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "script": {"type": "string", "description": "Nombre del script npm"},
        },
        "required": ["path", "script"],
    },
    handler=npm_run,
))

register(ToolDef(
    name="run_tests",
    description="Ejecuta pytest en un directorio de proyecto Python.",
    category="dev", min_level=3,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "args": {"type": "string", "description": "Args adicionales para pytest", "default": ""},
        },
        "required": ["path"],
    },
    handler=run_tests,
))
