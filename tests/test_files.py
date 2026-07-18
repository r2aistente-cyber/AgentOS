"""Tests de upload/download/delete de archivos."""
from __future__ import annotations

import io


async def test_upload_retorna_metadata(client):
    content = b"hola mundo"
    r = await client.post("/api/v1/files/upload", files={"file": ("test.txt", io.BytesIO(content), "text/plain")})
    assert r.status_code == 200
    body = r.json()
    assert "file_id" in body
    assert body["filename"] == "test.txt"
    assert body["size"] == len(content)


async def test_list_files_incluye_subido(client):
    content = b"archivo de lista"
    up = await client.post("/api/v1/files/upload", files={"file": ("lista.txt", io.BytesIO(content), "text/plain")})
    file_id = up.json()["file_id"]

    r = await client.get("/api/v1/files")
    assert r.status_code == 200
    ids = [f["file_id"] for f in r.json()]
    assert file_id in ids


async def test_download_archivo(client):
    content = b"contenido descargable"
    up = await client.post("/api/v1/files/upload", files={"file": ("down.txt", io.BytesIO(content), "text/plain")})
    file_id = up.json()["file_id"]

    r = await client.get(f"/api/v1/files/{file_id}")
    assert r.status_code == 200
    assert r.content == content


async def test_download_archivo_inexistente_da_404(client):
    r = await client.get("/api/v1/files/id-que-no-existe-xyz")
    assert r.status_code == 404


async def test_delete_archivo(client):
    content = b"eliminar esto"
    up = await client.post("/api/v1/files/upload", files={"file": ("del.txt", io.BytesIO(content), "text/plain")})
    file_id = up.json()["file_id"]

    r = await client.delete(f"/api/v1/files/{file_id}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Ya no debe estar en el índice
    r2 = await client.get(f"/api/v1/files/{file_id}")
    assert r2.status_code == 404


async def test_delete_dos_veces_segundo_da_404(client):
    content = b"doble delete"
    up = await client.post("/api/v1/files/upload", files={"file": ("dd.txt", io.BytesIO(content), "text/plain")})
    file_id = up.json()["file_id"]

    await client.delete(f"/api/v1/files/{file_id}")
    r = await client.delete(f"/api/v1/files/{file_id}")
    assert r.status_code == 404


async def test_delete_inexistente_da_404(client):
    r = await client.delete("/api/v1/files/no-existe-jamás")
    assert r.status_code == 404


async def test_upload_archivo_binario(client):
    content = bytes(range(256))
    r = await client.post("/api/v1/files/upload", files={"file": ("bin.bin", io.BytesIO(content), "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["size"] == 256
