"""Tools de archivos (read, write, list, search) restringidas al sandbox."""
from __future__ import annotations

from security.sandbox import Sandbox
from tools.registry import ToolDef, register


def read_file(path: str) -> str:
    return Sandbox.resolve(path).read_text(encoding="utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    safe = Sandbox.resolve(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return f"Archivo escrito: {safe.name} ({len(content)} caracteres)"


def list_files(path: str = ".") -> str:
    safe = Sandbox.resolve(path)
    if not safe.exists():
        return f"Directorio no encontrado: {path}"
    entries = []
    for item in sorted(safe.iterdir()):
        icon = "📁" if item.is_dir() else "📄"
        size = f" ({item.stat().st_size}b)" if item.is_file() else ""
        entries.append(f"{icon} {item.name}{size}")
    return "\n".join(entries) if entries else "(vacío)"


def search_files(pattern: str = "*", path: str = ".") -> str:
    safe = Sandbox.resolve(path)
    matches = list(safe.rglob(pattern))[:50]
    if not matches:
        return f"Sin resultados para '{pattern}'"
    return "\n".join(str(m.relative_to(safe)) for m in matches)


register(ToolDef("read_file", "Lee el contenido de un archivo del sandbox.", "file",
    {"type": "object", "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
     "required": ["path"]}, read_file))

register(ToolDef("write_file", "Escribe (o sobrescribe) un archivo en el sandbox.", "file",
    {"type": "object", "properties": {
        "path": {"type": "string", "description": "Ruta del archivo"},
        "content": {"type": "string", "description": "Contenido"}},
     "required": ["path", "content"]}, write_file, dangerous=True))

register(ToolDef("list_files", "Lista archivos y carpetas del sandbox.", "file",
    {"type": "object", "properties": {"path": {"type": "string", "default": "."}}},
    list_files))

register(ToolDef("search_files", "Busca archivos por patrón glob en el sandbox.", "file",
    {"type": "object", "properties": {
        "pattern": {"type": "string", "description": "Patrón glob, ej: *.py"},
        "path": {"type": "string", "default": "."}},
     "required": ["pattern"]}, search_files))
