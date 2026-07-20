"""Tests del extractor de archivos (hub/templates/file_extractor.py).

Las librerías pesadas (pypdf, docx, openpyxl) se mockean para no
requerir instalación en CI.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# file_extractor no depende de agent_config — se importa directamente
_TEMPLATES = Path(__file__).resolve().parent.parent.parent / "hub" / "templates"


@pytest.fixture(autouse=True)
def _extractor_path():
    if str(_TEMPLATES) not in sys.path:
        sys.path.insert(0, str(_TEMPLATES))
    yield
    if str(_TEMPLATES) in sys.path:
        sys.path.remove(str(_TEMPLATES))


# ─── Archivos de texto plano ──────────────────────────────────────────────────

def test_extract_txt(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "doc.txt"
    f.write_text("Hola mundo", encoding="utf-8")
    assert extract_text(f) == "Hola mundo"


def test_extract_md(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "doc.md"
    f.write_text("# Título", encoding="utf-8")
    assert "Título" in extract_text(f)


def test_extract_json(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "data.json"
    f.write_text('{"key": "value"}', encoding="utf-8")
    assert '"key"' in extract_text(f)


def test_extract_yaml(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "config.yaml"
    f.write_text("name: test\nvalue: 42", encoding="utf-8")
    result = extract_text(f)
    assert "name" in result


def test_extract_limite_20k_chars(tmp_path):
    from file_extractor import extract_text, _MAX_CHARS
    f = tmp_path / "grande.txt"
    f.write_text("x" * (_MAX_CHARS + 5000), encoding="utf-8")
    result = extract_text(f)
    assert len(result) == _MAX_CHARS


# ─── CSV ──────────────────────────────────────────────────────────────────────

def test_extract_csv(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "datos.csv"
    f.write_text("nombre,edad\nJuan,30\nMaría,25", encoding="utf-8")
    result = extract_text(f)
    assert "nombre" in result
    assert "Juan" in result


def test_extract_csv_muchas_filas(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "grande.csv"
    lines = ["col1,col2"] + [f"fila{i},val{i}" for i in range(600)]
    f.write_text("\n".join(lines), encoding="utf-8")
    result = extract_text(f)
    assert "filas total" in result  # mensaje de truncado


# ─── Extensión no soportada ───────────────────────────────────────────────────

def test_extract_extension_no_soportada(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "archivo.xyz"
    f.write_text("contenido")
    assert extract_text(f) == ""


def test_extract_extension_exe_retorna_vacio(tmp_path):
    from file_extractor import extract_text
    f = tmp_path / "app.exe"
    f.write_bytes(b"\x4d\x5a" + b"\x00" * 100)
    assert extract_text(f) == ""


# ─── PDF (mock pypdf) ────────────────────────────────────────────────────────

def test_extract_pdf_con_pypdf(tmp_path):
    from file_extractor import extract_text

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Texto del PDF"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    mock_pypdf = MagicMock()
    mock_pypdf.PdfReader.return_value = mock_reader

    with patch.dict("sys.modules", {"pypdf": mock_pypdf}):
        # Forzar reimport del módulo
        import importlib
        import file_extractor
        importlib.reload(file_extractor)
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF-1.4")
        result = file_extractor.extract_text(f)

    assert "Texto del PDF" in result


def test_extract_pdf_sin_pypdf(tmp_path):
    from file_extractor import extract_text

    with patch.dict("sys.modules", {"pypdf": None}):
        import importlib
        import file_extractor
        importlib.reload(file_extractor)
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"%PDF")
        result = file_extractor.extract_text(f)

    assert "pypdf" in result or "no instalado" in result or "[Error" in result


# ─── DOCX (mock python-docx) ─────────────────────────────────────────────────

def test_extract_docx_con_docx(tmp_path):
    from file_extractor import extract_text

    mock_para = MagicMock()
    mock_para.text = "Párrafo del documento."
    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]

    mock_docx_mod = MagicMock()
    mock_docx_mod.Document.return_value = mock_doc

    with patch.dict("sys.modules", {"docx": mock_docx_mod}):
        import importlib
        import file_extractor
        importlib.reload(file_extractor)
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK")
        result = file_extractor.extract_text(f)

    assert "Párrafo del documento." in result


def test_extract_docx_sin_libreria(tmp_path):
    with patch.dict("sys.modules", {"docx": None}):
        import importlib
        import file_extractor
        importlib.reload(file_extractor)
        f = tmp_path / "doc.docx"
        f.write_bytes(b"PK")
        result = file_extractor.extract_text(f)

    assert "python-docx" in result or "no instalado" in result or "[Error" in result


# ─── XLSX (mock openpyxl) ────────────────────────────────────────────────────

def test_extract_xlsx_con_openpyxl(tmp_path):
    from file_extractor import extract_text

    mock_row = ("Columna A", "Columna B")
    mock_sheet = MagicMock()
    mock_sheet.title = "Hoja1"
    mock_sheet.iter_rows.return_value = [mock_row]
    mock_wb = MagicMock()
    mock_wb.worksheets = [mock_sheet]

    mock_openpyxl = MagicMock()
    mock_openpyxl.load_workbook.return_value = mock_wb

    with patch.dict("sys.modules", {"openpyxl": mock_openpyxl}):
        import importlib
        import file_extractor
        importlib.reload(file_extractor)
        f = tmp_path / "datos.xlsx"
        f.write_bytes(b"PK")
        result = file_extractor.extract_text(f)

    assert "Hoja1" in result
    assert "Columna A" in result


# ─── Error en extracción ──────────────────────────────────────────────────────

def test_extract_error_retorna_mensaje_no_crash(tmp_path):
    from file_extractor import extract_text

    f = tmp_path / "corrupto.txt"
    f.write_bytes(b"\xff\xfe")  # bytes que pueden causar error de codificación extrema

    # No debe lanzar excepción — retorna string (puede ser el contenido o un mensaje de error)
    result = extract_text(f)
    assert isinstance(result, str)
