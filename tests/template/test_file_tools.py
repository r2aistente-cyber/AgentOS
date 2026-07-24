"""Tests de read_file: lectura completa y paginación por rango de líneas.

Agregado junto con la paginación (start_line/end_line) — antes read_file
siempre leía el archivo entero, lo que combinado con el truncado a
MAX_TOOL_OUTPUT (engine.py) dejaba al LLM sin forma de pedir el resto de
un archivo largo sin inventarse parámetros (visto en producción: intentó
`offset`, después `start_line/end_line/limit` sin que existiera ninguno).
"""
from __future__ import annotations


def _write(template_env, name: str, content: str) -> None:
    (template_env["data_dir"] / name).write_text(content, encoding="utf-8")


def test_read_file_completo_sin_rango(template_env):
    from tools.base_tools.file_tools import read_file

    _write(template_env, "a.txt", "uno\ndos\ntres")
    assert read_file("a.txt") == "uno\ndos\ntres"


def test_read_file_rango_intermedio(template_env):
    from tools.base_tools.file_tools import read_file

    _write(template_env, "b.txt", "\n".join(f"linea{i}" for i in range(1, 11)))  # 10 líneas
    result = read_file("b.txt", start_line=3, end_line=5)
    assert result == "[líneas 3-5 de 10]\nlinea3\nlinea4\nlinea5"


def test_read_file_solo_start_line_llega_hasta_el_final(template_env):
    from tools.base_tools.file_tools import read_file

    _write(template_env, "c.txt", "\n".join(f"linea{i}" for i in range(1, 6)))  # 5 líneas
    result = read_file("c.txt", start_line=4)
    assert result == "[líneas 4-5 de 5]\nlinea4\nlinea5"


def test_read_file_end_line_mayor_al_total_se_capea(template_env):
    from tools.base_tools.file_tools import read_file

    _write(template_env, "d.txt", "uno\ndos")  # 2 líneas
    result = read_file("d.txt", start_line=1, end_line=999)
    assert result == "[líneas 1-2 de 2]\nuno\ndos"


def test_read_file_start_line_fuera_de_rango(template_env):
    from tools.base_tools.file_tools import read_file

    _write(template_env, "e.txt", "uno\ndos")  # 2 líneas
    result = read_file("e.txt", start_line=50)
    assert "fuera de rango" in result
    assert "2 líneas" in result


def test_read_file_tool_schema_declara_start_end_line():
    """El schema expuesto al LLM debe listar start_line/end_line — la causa
    original del bug era que el modelo no tenía dónde leer los parámetros
    reales y los inventó."""
    from tools.registry import get
    import tools.base_tools.file_tools  # noqa: F401  (registra read_file)

    tool = get("read_file")
    assert tool is not None
    props = tool.parameters["properties"]
    assert "start_line" in props
    assert "end_line" in props
    assert "offset" not in props
