"""Tests de GET /api/v1/hub/specialties y /specialties/{id}/preview —
los endpoints que usa el wizard de creación de agentes para listar
specialties y prellenar campos antes de crear el agente.

Mismo patrón que tests/test_hub_fs.py: FastAPI() + include_router +
TestClient, sin levantar el Hub completo. Aislamiento de filesystem igual
que tests/test_specialty_loader.py (hub.config.specialties_dir/skills_dir/
knowledge_dir/registry_path apuntan a tmp_path).
"""
from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def api_env(tmp_path):
    specialties = tmp_path / "specialties"
    specialties.mkdir()
    skills = tmp_path / "skills"
    skills.mkdir()
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    registry_path = tmp_path / "agents.json"

    (specialties / "core.json").write_text(
        '{"id": "core", "name": "R2 PRIME", "description": "Asistente base", '
        '"personality": {"system_prompt": "Eres el asistente base."}, '
        '"tools": {"allow": ["*"]}}',
        encoding="utf-8",
    )
    (specialties / "r2-legal.json").write_text(
        '{"id": "r2-legal", "name": "R2 Legal", "description": "Agente legal", '
        '"extends": ["core"], '
        '"personality": {"system_prompt": "Eres R2 Legal."}, '
        '"skills": ["derecho-general"], '
        '"skills_on_demand": ["escritura"], '
        '"tools": {"allow": ["read_file"]}}',
        encoding="utf-8",
    )
    (skills / "derecho-general.yaml").write_text(
        'description: "Conocimiento legal base"\nprompt: "Sos abogado."\n',
        encoding="utf-8",
    )
    (skills / "escritura.yaml").write_text(
        'description: "Redactar textos"\nprompt: "Reglas de redaccion."\n',
        encoding="utf-8",
    )

    import hub.config as cfg
    with patch.object(cfg, "specialties_dir", return_value=specialties), \
         patch.object(cfg, "skills_dir", return_value=skills), \
         patch.object(cfg, "knowledge_dir", return_value=knowledge), \
         patch.object(cfg, "registry_path", return_value=registry_path):
        sys.modules.pop("hub.api.agents", None)
        from hub.api.agents import router
        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)
        sys.modules.pop("hub.api.agents", None)


def test_list_specialties_devuelve_catalogo(api_env):
    r = api_env.get("/api/v1/hub/specialties")
    assert r.status_code == 200
    data = r.json()

    ids = {s["id"] for s in data}
    assert ids == {"core", "r2-legal"}

    r2legal = next(s for s in data if s["id"] == "r2-legal")
    assert r2legal["name"] == "R2 Legal"
    assert r2legal["description"] == "Agente legal"


def test_preview_specialty_trae_config_body_resuelto(api_env):
    r = api_env.get("/api/v1/hub/specialties/r2-legal/preview")
    assert r.status_code == 200
    data = r.json()

    assert "Eres R2 Legal." in data["config_body"]["system_prompt"]
    assert "activar_skill" in data["config_body"]["tools"]["allow"]


def test_preview_specialty_trae_skills_separadas_por_modo(api_env):
    r = api_env.get("/api/v1/hub/specialties/r2-legal/preview")
    data = r.json()

    assert data["always_on"] == [
        {"name": "derecho-general", "description": "Conocimiento legal base"}
    ]
    assert data["on_demand"] == [
        {"name": "escritura", "description": "Redactar textos"}
    ]


def test_preview_specialty_inexistente_da_404(api_env):
    r = api_env.get("/api/v1/hub/specialties/no-existe/preview")
    assert r.status_code == 404
