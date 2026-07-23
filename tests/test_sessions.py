"""Tests de sesiones — endpoints reales de hub/templates/agent_main.py.

Migrado desde la v1 (backend.main, ya eliminado). El shape de la API
cambió respecto al original: no hay endpoint de detalle combinado
{session, messages}, ni 404 en GET/DELETE de sesiones inexistentes, ni
soporte de ?limit= en el listado — se documentan esos huecos abajo en vez
de fingir que existen.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _template_support import (  # noqa: E402
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


@pytest.fixture(autouse=True)
def _template_env(tmp_path):
    cfg = default_config(tmp_path)
    cfg["agent"]["name"] = "sessions-test-agent"
    install_agent_config(tmp_path, cfg)

    yield

    cleanup_template_modules()


@pytest_asyncio.fixture
async def client(_template_env, tmp_path):
    import memory.db as db_mod
    db_mod._DB_PATH = tmp_path / "memory.db"
    from memory.db import init_db
    await init_db()

    import agent_main
    async with AsyncClient(transport=ASGITransport(app=agent_main.app), base_url="http://test") as c:
        yield c


async def test_new_session_retorna_id(client):
    r = await client.post("/api/v1/sessions", json={"user_id": "xavier", "title": "Test"})
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert len(body["id"]) == 36  # UUID v4


async def test_new_session_defaults(client):
    r = await client.post("/api/v1/sessions", json={})
    assert r.status_code == 201
    assert "id" in r.json()


async def test_list_sessions_incluye_creada(client):
    cr = await client.post("/api/v1/sessions", json={"user_id": "test_user", "title": "Mi sesión"})
    sid = cr.json()["id"]

    r = await client.get("/api/v1/sessions?user_id=test_user")
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sid in ids


async def test_list_sessions_vacio_usuario_inexistente(client):
    r = await client.get("/api/v1/sessions?user_id=fantasma_xyz_999")
    assert r.status_code == 200
    assert r.json() == []


async def test_session_messages_vacio_al_crear(client):
    cr = await client.post("/api/v1/sessions", json={"user_id": "xavier"})
    sid = cr.json()["id"]

    r = await client.get(f"/api/v1/sessions/{sid}/messages")
    assert r.status_code == 200
    assert r.json() == []


async def test_delete_session_archiva(client):
    cr = await client.post("/api/v1/sessions", json={"user_id": "xavier"})
    sid = cr.json()["id"]

    r = await client.delete(f"/api/v1/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["archived"] == sid

    # La sesión archivada ya no aparece en el listado
    r2 = await client.get("/api/v1/sessions?user_id=xavier")
    assert sid not in [s["id"] for s in r2.json()]


async def test_get_messages_sesion_inexistente_no_da_404(client):
    """GAP conocido: el endpoint no valida existencia, devuelve [] con 200
    en vez de 404. Documentado aquí en vez de simulado como si no existiera."""
    r = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000/messages")
    assert r.status_code == 200
    assert r.json() == []


async def test_delete_session_inexistente_no_da_404(client):
    """GAP conocido: mismo caso que arriba mapeado a DELETE."""
    r = await client.delete("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200


async def test_historial_orden_cronologico(client):
    """Los mensajes deben volver en orden cronológico, no invertido."""
    from memory import session as store

    sid = await store.create_session("xavier", "core")
    await store.add_message(sid, "user", "primero")
    await store.add_message(sid, "assistant", "segundo")
    await store.add_message(sid, "user", "tercero")

    history = await store.get_messages(sid)
    assert history[0]["content"] == "primero"
    assert history[-1]["content"] == "tercero"
