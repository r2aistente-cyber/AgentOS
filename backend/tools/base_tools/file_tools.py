"""Herramientas de sistema de archivos (read, write, list, search)."""
from __future__ import annotations

import json
from pathlib import Path

from backend.security.sandbox import Sandbox
from backend.tools.registry import ToolDef, register


def read_file(path: str) -> str:
    safe = Sandbox.resolve(path)
    return safe.read_text(encoding="utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    safe = Sandbox.resolve(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return f"Archivo escrito: {safe} ({len(content)} caracteres)"


def list_files(path: str = ".") -> str:
    safe = Sandbox.resolve(path)
    if not safe.exists():
        return f"Directorio no encontrado: {path}"
    entries = []
    for item in sorted(safe.iterdir()):
        icon = "📁" if item.is_dir() else "📄"
        size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
        entries.append(f"{icon} {item.name}{size}")
    return "\n".join(entries) if entries else "(vacío)"


def search_files(path: str = ".", pattern: str = "*") -> str:
    safe = Sandbox.resolve(path)
    matches = list(safe.rglob(pattern))[:50]
    if not matches:
        return f"Sin resultados para '{pattern}' en {path}"
    return "\n".join(str(m.relative_to(safe)) for m in matches)


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="read_file",
    description="Lee el contenido de un archivo. Usa rutas relativas al sandbox.",
    category="file",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
        "required": ["path"],
    },
    handler=read_file,
))

register(ToolDef(
    name="write_file",
    description="Escribe contenido en un archivo. Si existe, lo sobrescribe.",
    category="file",
    min_level=2,
    requires_confirmation=True,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta del archivo"},
            "content": {"type": "string", "description": "Contenido a escribir"},
        },
        "required": ["path", "content"],
    },
    handler=write_file,
))

register(ToolDef(
    name="list_files",
    description="Lista archivos y carpetas en un directorio del sandbox.",
    category="file",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Ruta del directorio", "default": "."}},
    },
    handler=list_files,
))

register(ToolDef(
    name="search_files",
    description="Busca archivos por patrón glob dentro del sandbox.",
    category="file",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directorio base", "default": "."},
            "pattern": {"type": "string", "description": "Patrón glob, ej: *.py"},
        },
        "required": ["pattern"],
    },
    handler=search_files,
))
