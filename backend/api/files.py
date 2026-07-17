"""Endpoints de upload / download de archivos."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.security.sandbox import Sandbox

router = APIRouter(prefix="/api/v1/files", tags=["files"])

_UPLOAD_DIR = Path.home() / ".r2" / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Índice en memoria: file_id → {filename, path, size}
_index: dict[str, dict] = {}


@router.post("/upload")
async def upload_file(file: UploadFile):
    file_id = str(uuid.uuid4())
    dest = _UPLOAD_DIR / f"{file_id}_{file.filename}"
    content = await file.read()
    dest.write_bytes(content)
    _index[file_id] = {
        "file_id": file_id,
        "filename": file.filename,
        "path": str(dest),
        "size": len(content),
    }
    return _index[file_id]


@router.get("")
async def list_files():
    return list(_index.values())


@router.get("/{file_id}")
async def download_file(file_id: str):
    meta = _index.get(file_id)
    if not meta:
        raise HTTPException(404, "Archivo no encontrado")
    path = Path(meta["path"])
    if not path.exists():
        raise HTTPException(410, "Archivo eliminado del disco")
    return FileResponse(path, filename=meta["filename"])


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    meta = _index.pop(file_id, None)
    if not meta:
        raise HTTPException(404, "Archivo no encontrado")
    path = Path(meta["path"])
    if path.exists():
        path.unlink()
    return {"ok": True, "deleted": meta["filename"]}
