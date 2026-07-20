"""Tests del endpoint de navegación de directorios (hub/api/fs.py)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hub.api.fs import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ─── Sin path: raíz ───────────────────────────────────────────────────────────

def test_sin_path_retorna_drives_y_home():
    r = client.get("/api/v1/hub/fs")
    assert r.status_code == 200
    data = r.json()
    assert "drives" in data
    assert "home" in data
    assert "dirs" in data
    assert data["dirs"] == []
    assert data["path"] == ""
    assert data["parent"] is None


def test_sin_path_home_existe():
    r = client.get("/api/v1/hub/fs")
    home = r.json()["home"]
    assert Path(home).exists()


# ─── Con path válido ───────────────────────────────────────────────────────────

def test_path_valido_lista_subdirectorios(tmp_path):
    (tmp_path / "carpeta_a").mkdir()
    (tmp_path / "carpeta_b").mkdir()
    (tmp_path / "archivo.txt").write_text("x")  # no debe aparecer

    r = client.get("/api/v1/hub/fs", params={"path": str(tmp_path)})
    assert r.status_code == 200
    data = r.json()
    assert "carpeta_a" in data["dirs"]
    assert "carpeta_b" in data["dirs"]
    assert "archivo.txt" not in data["dirs"]


def test_path_valido_retorna_parent(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    r = client.get("/api/v1/hub/fs", params={"path": str(subdir)})
    data = r.json()
    assert data["path"] == str(subdir)
    assert data["parent"] == str(tmp_path)


def test_path_valido_ocultos_excluidos(tmp_path):
    (tmp_path / ".oculto").mkdir()
    (tmp_path / "visible").mkdir()

    r = client.get("/api/v1/hub/fs", params={"path": str(tmp_path)})
    data = r.json()
    assert "visible" in data["dirs"]
    assert ".oculto" not in data["dirs"]


def test_path_valido_dirs_ordenados(tmp_path):
    for name in ["z_last", "a_first", "m_mid"]:
        (tmp_path / name).mkdir()

    r = client.get("/api/v1/hub/fs", params={"path": str(tmp_path)})
    dirs = r.json()["dirs"]
    assert dirs == sorted(dirs, key=str.lower)


# ─── Path inexistente ─────────────────────────────────────────────────────────

def test_path_inexistente_retorna_404():
    r = client.get("/api/v1/hub/fs", params={"path": "/ruta/que/no/existe/jamas/12345"})
    assert r.status_code == 404


def test_path_es_archivo_no_directorio_retorna_404(tmp_path):
    f = tmp_path / "archivo.txt"
    f.write_text("x")
    r = client.get("/api/v1/hub/fs", params={"path": str(f)})
    assert r.status_code == 404


# ─── Sin permisos ─────────────────────────────────────────────────────────────

def test_path_sin_permisos_retorna_403(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    original_scandir = os.scandir

    def _raise_permission(*args, **kwargs):
        raise PermissionError("Access denied")

    with patch("hub.api.fs.os.scandir", side_effect=_raise_permission):
        r = client.get("/api/v1/hub/fs", params={"path": str(locked)})

    assert r.status_code == 403


# ─── Drives ───────────────────────────────────────────────────────────────────

def test_drives_en_linux_retorna_slash():
    """En Linux, _drives() debe retornar ['/']."""
    if os.name == "nt":
        pytest.skip("Solo aplica en Linux/macOS")
    r = client.get("/api/v1/hub/fs")
    assert "/" in r.json()["drives"]
