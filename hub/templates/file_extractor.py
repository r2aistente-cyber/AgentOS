"""Extracción de texto de archivos adjuntos.

Soporta: TXT, MD, JSON, CSV, PDF (pypdf), DOCX (python-docx), XLSX (openpyxl).
Las librerías de terceros se importan lazily — si no están instaladas se
devuelve un mensaje de fallback en vez de romper el agente.
"""
from __future__ import annotations

from pathlib import Path

_MAX_CHARS = 20_000  # límite para no saturar el contexto del LLM


def extract_text(path: Path) -> str:
    """Devuelve el texto extraído del archivo, o '' si no es soportado."""
    suffix = path.suffix.lower()
    try:
        if suffix in (".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".log"):
            return _read_plain(path)
        if suffix == ".csv":
            return _read_csv(path)
        if suffix == ".pdf":
            return _read_pdf(path)
        if suffix in (".doc", ".docx"):
            return _read_docx(path)
        if suffix in (".xls", ".xlsx"):
            return _read_xlsx(path)
    except Exception as e:
        return f"[Error extrayendo {path.name}: {e}]"
    return ""


def _read_plain(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:_MAX_CHARS]


def _read_csv(path: Path) -> str:
    import csv
    rows = []
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i > 500:
                rows.append(f"... ({i} filas total, mostrando primeras 500)")
                break
            rows.append(", ".join(row))
    return "\n".join(rows)[:_MAX_CHARS]


def _read_pdf(path: Path) -> str:
    try:
        import pypdf
    except ImportError:
        return f"[pypdf no instalado — instala con: pip install pypdf]"

    reader = pypdf.PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
        if sum(len(p) for p in parts) > _MAX_CHARS:
            break
    return "\n".join(parts)[:_MAX_CHARS]


def _read_docx(path: Path) -> str:
    try:
        import docx
    except ImportError:
        return f"[python-docx no instalado — instala con: pip install python-docx]"

    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)[:_MAX_CHARS]


def _read_xlsx(path: Path) -> str:
    try:
        import openpyxl
    except ImportError:
        return f"[openpyxl no instalado — instala con: pip install openpyxl]"

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        parts.append(f"=== Hoja: {sheet.title} ===")
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i > 300:
                parts.append("... (filas adicionales omitidas)")
                break
            row_str = "\t".join(str(v) if v is not None else "" for v in row)
            if row_str.strip():
                parts.append(row_str)
        if sum(len(p) for p in parts) > _MAX_CHARS:
            break
    return "\n".join(parts)[:_MAX_CHARS]
