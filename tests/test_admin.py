"""Tests de admin: usuarios, permisos y auditoría."""
from __future__ import annotations

import uuid


def _uid():
    return f"user_{uuid.uuid4().hex[:8]}"


async def test_crear_usuario(client):
    uid = _uid()
    r = await client.post("/api/v1/admin/users", json={"id": uid, "name": "Test User", "role": "user", "permission_level": 1})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["user_id"] == uid


async def test_crear_usuario_defaults(client):
    uid = _uid()
    r = await client.post("/api/v1/admin/users", json={"id": uid, "name": "Solo nombre"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_upsert_usuario_actualiza(client):
    uid = _uid()
    await client.post("/api/v1/admin/users", json={"id": uid, "name": "Original", "permission_level": 1})
    r = await client.post("/api/v1/admin/users", json={"id": uid, "name": "Actualizado", "permission_level": 2})
    assert r.status_code == 200

    # Verificar en la lista
    users = await client.get("/api/v1/admin/users")
    found = next((u for u in users.json() if u["id"] == uid), None)
    assert found is not None
    assert found["name"] == "Actualizado"
    assert found["permission_level"] == 2


async def test_crear_usuario_nivel_invalido(client):
    r = await client.post("/api/v1/admin/users", json={"id": _uid(), "name": "X", "permission_level": 9})
    assert r.status_code == 400


async def test_crear_usuario_nivel_negativo(client):
    r = await client.post("/api/v1/admin/users", json={"id": _uid(), "name": "X", "permission_level": -1})
    assert r.status_code == 400


async def test_list_usuarios(client):
    uid = _uid()
    await client.post("/api/v1/admin/users", json={"id": uid, "name": "Listable"})
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    ids = [u["id"] for u in r.json()]
    assert uid in ids


async def test_set_permission(client):
    uid = _uid()
    await client.post("/api/v1/admin/users", json={"id": uid, "name": "Permiso Test", "permission_level": 1})
    r = await client.post("/api/v1/admin/permissions", json={"user_id": uid, "level": 3})
    assert r.status_code == 200
    assert r.json()["ok"] is True

    users = await client.get("/api/v1/admin/users")
    found = next(u for u in users.json() if u["id"] == uid)
    assert found["permission_level"] == 3


async def test_set_permission_nivel_invalido(client):
    r = await client.post("/api/v1/admin/permissions", json={"user_id": "xavier", "level": 99})
    assert r.status_code == 400


async def test_audit_log_vacio_por_defecto(client):
    r = await client.get("/api/v1/admin/audit?user_id=user_que_no_existe_xyzabc")
    assert r.status_code == 200
    assert r.json() == []


async def test_audit_filtro_por_tool(client):
    r = await client.get("/api/v1/admin/audit?tool_name=read_file")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_audit_limit(client):
    r = await client.get("/api/v1/admin/audit?limit=1")
    assert r.status_code == 200
    assert len(r.json()) <= 1


async def test_usuario_xavier_existe_por_defecto(client):
    """Xavier se inserta en init_db. Debe aparecer en la lista."""
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 200
    ids = [u["id"] for u in r.json()]
    assert "xavier" in ids
