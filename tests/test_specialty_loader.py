"""Tests de hub/specialty_loader.py: resolución de specialties/*.json +
skills/*.yaml a un config_body para AgentManager.create().

Aislamiento: hub.config.specialties_dir/skills_dir/knowledge_dir apuntan a
tmp_path — nunca se leen los specialties/skills reales del repo.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def loader_env(tmp_path):
    specialties = tmp_path / "specialties"
    specialties.mkdir()
    skills = tmp_path / "skills"
    skills.mkdir()
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()

    (specialties / "core.json").write_text(
        '{"id": "core", "personality": {"system_prompt": "Eres el asistente base."}, '
        '"tools": {"allow": ["*"]}, "skills": []}',
        encoding="utf-8",
    )
    (specialties / "hija.json").write_text(
        '{"id": "hija", "extends": ["core"], '
        '"personality": {"system_prompt": "Eres la especialidad hija."}, '
        '"tools": {"allow": ["read_file"]}, '
        '"mcp_servers": [{"name": "suite_legal", "url": "http://x/mcp", "api_key": "k"}], '
        '"skills": ["skill-a"], '
        '"knowledge_files": ["existe.yaml", "no-existe.pdf"]}',
        encoding="utf-8",
    )
    (skills / "skill-a.yaml").write_text(
        yaml.safe_dump({
            "prompt": "Prompt de la skill A.",
            "tools": ["write_file", "read_file"],
            "knowledge_files": ["de-la-skill.yaml"],
        }),
        encoding="utf-8",
    )
    (knowledge / "existe.yaml").write_text("contenido: si", encoding="utf-8")
    (knowledge / "de-la-skill.yaml").write_text("contenido: skill", encoding="utf-8")

    import hub.config as cfg
    with patch.object(cfg, "specialties_dir", return_value=specialties), \
         patch.object(cfg, "skills_dir", return_value=skills), \
         patch.object(cfg, "knowledge_dir", return_value=knowledge):
        yield {"specialties": specialties, "skills": skills, "knowledge": knowledge}


def test_tools_allow_del_hijo_reemplaza_al_padre_no_se_une(loader_env):
    """core.tools.allow=['*'] no debe filtrarse a un specialty más
    restringido — de lo contrario cualquier hijo terminaría con acceso
    total sin importar lo que declare."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija")
    allow = result["config_body"]["tools"]["allow"]

    assert "*" not in allow
    assert set(allow) == {"read_file", "write_file"}


def test_system_prompt_concatena_specialty_y_skills(loader_env):
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija")
    prompt = result["config_body"]["system_prompt"]

    assert "Eres la especialidad hija." in prompt
    assert "Prompt de la skill A." in prompt


def test_knowledge_files_existentes_se_resuelven_y_faltantes_se_reportan(loader_env):
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija")

    resolved_names = {p.name for p in result["knowledge_source_files"]}
    assert resolved_names == {"existe.yaml", "de-la-skill.yaml"}
    assert result["missing_knowledge_files"] == ["no-existe.pdf"]


def test_mcp_servers_config_pasa_intacto(loader_env):
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija")
    assert result["config_body"]["mcp_servers"] == [
        {"name": "suite_legal", "url": "http://x/mcp", "api_key": "k"}
    ]


def test_specialty_inexistente_da_filenotfound(loader_env):
    from hub import specialty_loader

    with pytest.raises(FileNotFoundError):
        specialty_loader.resolve_specialty("no-existe")
