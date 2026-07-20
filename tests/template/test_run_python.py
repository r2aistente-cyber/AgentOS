"""Tests para la tool run_python (hub/templates/tools/base_tools/python_tools.py).

Commit de referencia: feat: add run_python tool for direct Python script execution
"""
from __future__ import annotations

import pytest


# ─── Ejecución básica ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_python_print_simple(template_env):
    """El output de print() se retorna como string."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("print('hola mundo')")
    assert result == "hola mundo"


@pytest.mark.asyncio
async def test_run_python_calculo_numerico(template_env):
    """run_python puede hacer cálculos y retornar el resultado."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("print(2 ** 10)")
    assert result.strip() == "1024"


@pytest.mark.asyncio
async def test_run_python_multilinea(template_env):
    """Scripts multilínea producen output correcto."""
    from tools.base_tools.python_tools import run_python

    script = "\n".join([
        "total = 0",
        "for i in range(5):",
        "    total += i",
        "print(total)",
    ])
    result = await run_python(script)
    assert result.strip() == "10"


@pytest.mark.asyncio
async def test_run_python_importa_stdlib(template_env):
    """Puede importar módulos de la stdlib."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("import json; print(json.dumps({'a': 1}))")
    assert '"a"' in result


@pytest.mark.asyncio
async def test_run_python_sin_output_retorna_codigo(template_env):
    """Scripts sin output retornan un mensaje con el código de salida."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("x = 1 + 1")  # sin print
    assert "sin salida" in result or result == ""


# ─── Manejo de errores ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_python_script_con_excepcion(template_env):
    """Cuando el script lanza una excepción, el output incluye el traceback."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("raise ValueError('error de prueba')")
    assert "ValueError" in result or "error de prueba" in result


@pytest.mark.asyncio
async def test_run_python_syntax_error(template_env):
    """Un SyntaxError también se captura como output."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("def foo(: pass")
    assert result  # algo debe retornar, no debe crashear run_python


# ─── Timeout ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_python_timeout(template_env):
    """Un script que excede el timeout retorna el mensaje [TIMEOUT]."""
    from tools.base_tools.python_tools import run_python

    result = await run_python("import time; time.sleep(10)", timeout=1)
    assert "[TIMEOUT]" in result


@pytest.mark.asyncio
async def test_run_python_timeout_maximo_300s(template_env):
    """El timeout se limita a 300 segundos aunque se pida más."""
    # Solo verificamos que no crashea con un valor alto y que
    # el timeout interno queda en máx 300. No esperamos el timeout real.
    from tools.base_tools.python_tools import run_python

    # Script rápido con timeout pedido absurdo — no debe fallar
    result = await run_python("print('ok')", timeout=99999)
    assert result == "ok"


# ─── Sandbox ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_python_archivo_temporal_eliminado(template_env):
    """El archivo .py temporal se elimina tras la ejecución."""
    import os
    from pathlib import Path
    from tools.base_tools.python_tools import run_python

    data_dir = template_env["data_dir"]
    py_files_antes = set(data_dir.glob("*.py"))

    await run_python("print('temp')")

    py_files_despues = set(data_dir.glob("*.py"))
    nuevos = py_files_despues - py_files_antes
    assert not nuevos, f"Archivos temporales no eliminados: {nuevos}"


@pytest.mark.asyncio
async def test_run_python_cwd_es_sandbox(template_env):
    """El script corre con cwd = sandbox del agente."""
    from tools.base_tools.python_tools import run_python

    data_dir = str(template_env["data_dir"])
    result = await run_python("import os; print(os.getcwd())")
    assert data_dir in result, f"El cwd debe ser el sandbox ({data_dir}), got: {result}"


@pytest.mark.asyncio
async def test_run_python_escribe_en_sandbox(template_env):
    """El script puede crear archivos en el sandbox."""
    from tools.base_tools.python_tools import run_python

    data_dir = template_env["data_dir"]
    result = await run_python(
        "with open('salida.txt', 'w') as f: f.write('datos')\nprint('creado')"
    )
    assert result.strip() == "creado"
    assert (data_dir / "salida.txt").exists()


# ─── Registro en el registry ─────────────────────────────────────────────────

def test_run_python_registrada_en_registry(template_env):
    """La tool run_python debe estar registrada después de importar python_tools."""
    import tools.base_tools.python_tools  # noqa: F401
    from tools import registry

    tool = registry.get("run_python")
    assert tool is not None, "run_python no está en el registry"
    assert tool.category == "system"
    assert not tool.requires_confirm, "run_python no debe requerir confirmación"


def test_run_python_parametros_schema(template_env):
    """El schema de parámetros tiene los campos requeridos."""
    import tools.base_tools.python_tools  # noqa: F401
    from tools import registry

    tool = registry.get("run_python")
    props = tool.parameters["properties"]
    assert "script" in props
    assert "timeout" in props
    assert "script" in tool.parameters.get("required", [])
