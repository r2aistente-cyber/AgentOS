"""Tests de tools de memoria a largo plazo (hub/templates/tools/base_tools/memory_tools.py)."""
from __future__ import annotations

import pytest


# ─── save_memory ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_memory_retorna_confirmacion(db):
    from tools.base_tools.memory_tools import save_memory
    result = await save_memory("clave1", "valor1")
    assert "clave1" in result


@pytest.mark.asyncio
async def test_save_memory_guarda_y_recupera(db):
    from tools.base_tools.memory_tools import save_memory, get_memory
    await save_memory("mi_clave", "mi_valor")
    result = await get_memory("mi_clave")
    assert result == "mi_valor"


@pytest.mark.asyncio
async def test_save_memory_con_categoria(db):
    from tools.base_tools.memory_tools import save_memory, list_memories
    await save_memory("k", "v", category="trabajo")
    result = await list_memories(category="trabajo")
    assert "k" in result


@pytest.mark.asyncio
async def test_save_memory_actualiza_sin_duplicar(db):
    from tools.base_tools.memory_tools import save_memory, get_memory, list_memories
    await save_memory("clave_unica", "valor_inicial")
    await save_memory("clave_unica", "valor_actualizado")

    result = await get_memory("clave_unica")
    assert result == "valor_actualizado"

    # Solo debe existir una entrada con esa clave
    all_memories = await list_memories()
    count = all_memories.count("clave_unica")
    assert count == 1


# ─── get_memory ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_memory_clave_inexistente(db):
    from tools.base_tools.memory_tools import get_memory
    result = await get_memory("clave_que_no_existe_xyzw")
    assert "No encontrado" in result


@pytest.mark.asyncio
async def test_get_memory_multiples_claves(db):
    from tools.base_tools.memory_tools import save_memory, get_memory
    await save_memory("clave_a", "alpha")
    await save_memory("clave_b", "beta")
    assert await get_memory("clave_a") == "alpha"
    assert await get_memory("clave_b") == "beta"


# ─── list_memories ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_memories_vacia(db):
    from tools.base_tools.memory_tools import list_memories
    result = await list_memories()
    assert "Sin memorias" in result


@pytest.mark.asyncio
async def test_list_memories_muestra_entradas(db):
    from tools.base_tools.memory_tools import save_memory, list_memories
    await save_memory("dato1", "contenido1")
    await save_memory("dato2", "contenido2")
    result = await list_memories()
    assert "dato1" in result
    assert "dato2" in result


@pytest.mark.asyncio
async def test_list_memories_filtra_por_categoria(db):
    from tools.base_tools.memory_tools import save_memory, list_memories
    await save_memory("trabajo_key", "trabajo_val", category="trabajo")
    await save_memory("personal_key", "personal_val", category="personal")

    trabajo = await list_memories(category="trabajo")
    assert "trabajo_key" in trabajo
    assert "personal_key" not in trabajo

    personal = await list_memories(category="personal")
    assert "personal_key" in personal
    assert "trabajo_key" not in personal


# ─── Registro en el registry ─────────────────────────────────────────────────

def test_memory_tools_registradas(template_env):
    import tools.base_tools.memory_tools  # noqa: F401
    from tools import registry
    names = {t.name for t in registry.all_tools()}
    assert "save_memory" in names
    assert "get_memory" in names
    assert "list_memories" in names
