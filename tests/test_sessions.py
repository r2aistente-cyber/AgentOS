"""Tests de sesiones — GET/POST/DELETE + historial."""
from __future__ import annotations


async def test_new_session_retorna_session_id(client):
    r = await client.post("/api/v1/sessions/new", json={"user_id": "xavier", "specialty_id": "core"})
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert len(body["session_id"]) == 36  # UUID v4


async def test_new_session_defaults(client):
    r = await client.post("/api/v1/sessions/new", json={})
    assert r.status_code == 200
    assert "session_id" in r.json()


async def test_list_sessions_usuario(client):
    await client.post("/api/v1/sessions/new", json={"user_id": "test_user", "title": "Mi sesión"})
    r = await client.get("/api/v1/sessions?user_id=test_user")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(s["user_id"] == "test_user" for s in data)


async def test_list_sessions_vacio_usuario_inexistente(client):
    r = await client.get("/api/v1/sessions?user_id=fantasma_xyz_999")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_session_detalle(client):
    cr = await client.post("/api/v1/sessions/new", json={"user_id": "xavier", "title": "Test detalle"})
    sid = cr.json()["session_id"]

    r = await client.get(f"/api/v1/sessions/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert "session" in body
    assert "messages" in body
    assert body["session"]["id"] == sid
    assert isinstance(body["messages"], list)


async def test_get_session_inexistente_da_404(client):
    r = await client.get("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_delete_session_archiva(client):
    cr = await client.post("/api/v1/sessions/new", json={"user_id": "xavier"})
    sid = cr.json()["session_id"]

    r = await client.delete(f"/api/v1/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # La sesión archivada no debe aparecer en GET
    r2 = await client.get(f"/api/v1/sessions/{sid}")
    assert r2.status_code == 404


async def test_delete_sesion_inexistente_da_404(client):
    r = await client.delete("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_list_sessions_limit(client):
    for i in range(5):
        await client.post("/api/v1/sessions/new", json={"user_id": "limit_user"})
    r = await client.get("/api/v1/sessions?user_id=limit_user&limit=2")
    assert r.status_code == 200
    assert len(r.json()) <= 2


async def test_historial_orden_cronologico(client):
    """Los mensajes deben volver en orden cronológico, no invertido."""
    from backend.memory import session as store

    sid = await store.create_session("xavier", "core")
    await store.add_message(sid, "user", "primero")
    await store.add_message(sid, "assistant", "segundo")
    await store.add_message(sid, "user", "tercero")

    history = await store.get_history(sid)
    assert history[0]["content"] == "primero"
    assert history[-1]["content"] == "tercero"
