"""Tests de upload/list de archivos — endpoints reales de agent_main.py.

Migrado desde la v1 (backend.main, ya eliminado). El endpoint actual es
más simple que el original: sube y lista por nombre de archivo, pero no
tiene download ni delete por id (`/api/v1/files/{file_id}` no existe).
Esa es una funcionalidad real que se perdió en la reestructuración —
documentada aquí en vez de testeada como si existiera.
"""
from __future__ import annotations

import io
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
    cfg["agent"]["name"] = "files-test-agent"
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


async def test_upload_retorna_metadata(client):
    content = b"hola mundo"
    r = await client.post("/api/v1/upload", files={"file": ("test.txt", io.BytesIO(content), "text/plain")})
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "test.txt"
    assert body["size"] == len(content)


async def test_list_files_incluye_subido(client):
    content = b"archivo de lista"
    await client.post("/api/v1/upload", files={"file": ("lista.txt", io.BytesIO(content), "text/plain")})

    r = await client.get("/api/v1/files")
    assert r.status_code == 200
    names = [f["name"] for f in r.json()]
    assert "lista.txt" in names


async def test_upload_archivo_binario(client):
    content = bytes(range(256))
    r = await client.post("/api/v1/upload", files={"file": ("bin.bin", io.BytesIO(content), "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["size"] == 256


async def test_files_sin_directorio_retorna_vacio(client):
    r = await client.get("/api/v1/files")
    assert r.status_code == 200
    assert r.json() == []
