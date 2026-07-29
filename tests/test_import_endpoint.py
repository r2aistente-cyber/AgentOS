"""Test end-to-end de POST /api/v1/hub/agents/import — el endpoint HTTP en
sí, no solo hub/importer.py aislado (ver tests/test_importer.py) ni el
roundtrip por debajo del Hub (ver tests/test_roundtrip.py). Cubre el
hardening real de esta sesión: reserve_port/release_port (antes
_next_port() se llamaba fuera del lock del manager) y la verificación
post-import que ahora intenta arrancar el agente en vez de devolver un 201
ciego con status="offline" sin haber comprobado nada.

Mismo patrón que tests/test_specialties_api.py: FastAPI() + include_router
+ TestClient, con hub.config apuntando a tmp_path.
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hub import exporter

_FAKE_AGENT_MAIN = """
from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
"""


@pytest.fixture
def api_env(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    registry_path = tmp_path / "agents.json"

    import hub.config as cfg
    with patch.object(cfg, "agents_dir", return_value=agents_dir), \
         patch.object(cfg, "registry_path", return_value=registry_path), \
         patch.object(cfg, "port_range", return_value=(9500, 9510)):
        sys.modules.pop("hub.api.agents", None)
        from hub.api.agents import router
        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)
        sys.modules.pop("hub.api.agents", None)


def _paquete_valido() -> bytes:
    origen = None
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp())
    origen = tmp / "agente-import-test"
    origen.mkdir()
    config = {
        "agent": {"name": "agente-import-test", "port": 9999},
        "security": {"level": 2, "token": "no-deberia-viajar"},
    }
    (origen / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (origen / "agent_main.py").write_text(_FAKE_AGENT_MAIN, encoding="utf-8")
    return exporter.export_agent("agente-import-test", origen)


def test_rechaza_archivo_que_no_es_tar_gz(api_env):
    r = api_env.post(
        "/api/v1/hub/agents/import",
        files={"file": ("agente.zip", b"contenido falso", "application/zip")},
    )
    assert r.status_code == 400
    assert "tar.gz" in r.json()["detail"]


def test_import_exitoso_arranca_y_queda_online(api_env):
    pkg = _paquete_valido()

    r = api_env.post(
        "/api/v1/hub/agents/import",
        files={"file": ("agente-import-test-export.tar.gz", pkg, "application/gzip")},
    )
    assert r.status_code == 201, r.text
    data = r.json()

    try:
        assert data["name"] == "agente-import-test"
        assert 9500 <= data["port"] <= 9510
        # Antes esto quedaba "offline" sin más -- ahora el endpoint intenta
        # arrancarlo de verdad (agent_main.py fake responde /api/v1/health).
        assert data["status"] == "online"
        assert "import_warning" not in data
    finally:
        from hub.api.agents import manager
        try:
            manager.stop("agente-import-test")
        except Exception:
            pass


def test_import_duplicado_no_pisa_el_puerto_del_primero(api_env):
    """Dos imports del mismo paquete original (con existing_names distinto
    en cada request real vendría del Hub, pero acá lo que importa es que
    reserve_port/release_port no entreguen el mismo puerto a ambos)."""
    pkg = _paquete_valido()

    r1 = api_env.post(
        "/api/v1/hub/agents/import",
        files={"file": ("a.tar.gz", pkg, "application/gzip")},
    )
    r2 = api_env.post(
        "/api/v1/hub/agents/import",
        files={"file": ("a.tar.gz", pkg, "application/gzip")},
    )
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["port"] != r2.json()["port"]
    assert r1.json()["name"] != r2.json()["name"]  # sufijo -2 por colisión de nombre

    from hub.api.agents import manager
    for name in (r1.json()["name"], r2.json()["name"]):
        try:
            manager.stop(name)
        except Exception:
            pass
