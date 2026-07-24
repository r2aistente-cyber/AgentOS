"""Tools de archivos (read, write, list, search) restringidas al sandbox."""
from __future__ import annotations

from pathlib import Path

from security.sandbox import Sandbox
from tools.registry import ToolContract, ToolDef, register


def read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """Lee un archivo entero, o un rango de líneas si se pasan start_line/end_line
    (1-indexado, inclusive). El resultado igual se trunca a MAX_TOOL_OUTPUT en el
    historial del LLM (engine.py) — el rango es lo que deja pedir la parte que
    falta sin releer el archivo completo de nuevo.
    """
    text = Sandbox.resolve(path).read_text(encoding="utf-8", errors="replace")
    if start_line is None and end_line is None:
        return text

    lines = text.splitlines()
    total = len(lines)
    start = max(1, start_line or 1)
    end = min(total, end_line or total)
    if start > total:
        return f"(el archivo tiene {total} líneas; start_line={start_line} está fuera de rango)"

    chunk = "\n".join(lines[start - 1:end])
    return f"[líneas {start}-{end} de {total}]\n{chunk}"


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


# ── Contratos de verificación (runtime, no LLM) ───────────────────────────────

def _pre_read(args: dict) -> tuple[bool, str]:
    try:
        p = Sandbox.resolve(args.get("path", ""))
        return (True, "") if p.exists() else (False, f"El archivo '{p}' no existe")
    except Exception as e:
        return (False, str(e))


def _post_write(args: dict, result: str) -> tuple[bool, str]:
    try:
        p = Sandbox.resolve(args.get("path", ""))
        if not p.exists():
            return (False, f"El archivo '{p}' no fue creado en disco")
        written_size = p.stat().st_size
        if written_size == 0 and args.get("content", ""):
            return (False, "El archivo está vacío en disco pero se envió contenido")
        return (True, "")
    except Exception as e:
        return (False, str(e))


# ── Registros ─────────────────────────────────────────────────────────────────

register(ToolDef(
    name="read_file",
    description=(
        "Lee el contenido de un archivo del sandbox. El resultado se trunca a "
        "2000 caracteres — para archivos más largos, usá start_line/end_line "
        "para pedir el rango que falta en vez de reintentar sin ellos."
    ),
    category="file",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta del archivo"},
            "start_line": {"type": "integer", "description": "Primera línea a devolver (1-indexado, opcional)"},
            "end_line": {"type": "integer", "description": "Última línea a devolver, inclusive (opcional)"},
        },
        "required": ["path"],
    },
    handler=read_file,
    contract=ToolContract(precondition=_pre_read),
))

register(ToolDef(
    name="write_file",
    description="Escribe (o sobrescribe) un archivo en el sandbox.",
    category="file",
    parameters={
        "type": "object",
        "properties": {
            "path":    {"type": "string", "description": "Ruta del archivo"},
            "content": {"type": "string", "description": "Contenido"},
        },
        "required": ["path", "content"],
    },
    handler=write_file,
    dangerous=True,
    contract=ToolContract(postcondition=_post_write),
))

register(ToolDef(
    name="list_files",
    description="Lista archivos y carpetas del sandbox.",
    category="file",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "default": "."}},
    },
    handler=list_files,
))

register(ToolDef(
    name="search_files",
    description="Busca archivos por patrón glob en el sandbox.",
    category="file",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Patrón glob, ej: *.py"},
            "path":    {"type": "string", "default": "."},
        },
        "required": ["pattern"],
    },
    handler=search_files,
))
