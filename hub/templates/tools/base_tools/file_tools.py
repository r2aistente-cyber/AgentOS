"""Tools de archivos (read, write, list, search) restringidas al sandbox."""
from __future__ import annotations

from pathlib import Path

from security.sandbox import Sandbox
from tools.registry import ToolContract, ToolDef, register


def read_file(path: str, start_line=None, end_line=None, limit=None) -> str:
    """Lee un archivo entero, o un rango de líneas si se pasan start_line/end_line
    y/o limit (1-indexado, inclusive). El resultado igual se trunca a
    MAX_TOOL_OUTPUT en el historial del LLM (engine.py) — el rango es lo que
    deja pedir la parte que falta sin releer el archivo completo de nuevo.

    Acepta start_line/end_line/limit como int o como string numérico (algunos
    modelos los mandan como string) — se castean acá en vez de dejar que
    truene un TypeError más abajo.
    """
    text = Sandbox.resolve(path).read_text(encoding="utf-8", errors="replace")
    if start_line is None and end_line is None and limit is None:
        return text

    start_line = int(start_line) if start_line is not None else None
    end_line = int(end_line) if end_line is not None else None
    limit = int(limit) if limit is not None else None

    lines = text.splitlines()
    total = len(lines)
    start = max(1, start_line or 1)
    if end_line is not None:
        end = min(total, end_line)
    elif limit is not None:
        end = min(total, start + limit - 1)
    else:
        end = total
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
        "2000 caracteres — para archivos más largos, pedí un rango con "
        "start_line/end_line, o los primeros N con limit. No existen otros "
        "parámetros (nada de 'offset')."
    ),
    category="file",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Ruta del archivo"},
            "start_line": {"type": "integer", "description": "Primera línea a devolver (1-indexado, opcional, default 1)"},
            "end_line": {"type": "integer", "description": "Última línea a devolver, inclusive (opcional)"},
            "limit": {"type": "integer", "description": "Máximo de líneas a devolver desde start_line (opcional, alternativa a end_line)"},
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
