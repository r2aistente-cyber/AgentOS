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
    (specialties / "hija-on-demand.json").write_text(
        '{"id": "hija-on-demand", "extends": ["core"], '
        '"personality": {"system_prompt": "Eres la especialidad hija."}, '
        '"tools": {"allow": ["read_file"]}, '
        '"skills": ["skill-a"], '
        '"skills_on_demand": ["skill-b"]}',
        encoding="utf-8",
    )
    (skills / "skill-b.yaml").write_text(
        yaml.safe_dump({
            "description": "Descripción corta de la skill B.",
            "prompt": "Prompt completo de la skill B.",
            "tools": ["exec_command"],
            "knowledge_files": ["de-la-skill-b.yaml"],
        }),
        encoding="utf-8",
    )
    (knowledge / "existe.yaml").write_text("contenido: si", encoding="utf-8")
    (knowledge / "de-la-skill.yaml").write_text("contenido: skill", encoding="utf-8")
    (knowledge / "de-la-skill-b.yaml").write_text("contenido: skill b", encoding="utf-8")

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


# ─── skills_on_demand: progressive discovery (no cargar todo siempre) ────────

def test_sin_skills_on_demand_no_cambia_nada(loader_env):
    """Una specialty sin `skills_on_demand` (como 'hija') se comporta
    exactamente igual que antes de este cambio — no regresión."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija")

    assert "skills" not in result["config_body"]
    assert "activar_skill" not in result["config_body"]["tools"]["allow"]
    assert "## Skills disponibles bajo demanda" not in result["config_body"]["system_prompt"]


def test_skills_on_demand_no_se_concatenan_al_prompt(loader_env):
    """El prompt COMPLETO de una skill on-demand no debe estar en el
    system_prompt final — solo su descripción, como parte del índice."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija-on-demand")
    prompt = result["config_body"]["system_prompt"]

    assert "Prompt completo de la skill B." not in prompt
    assert "Descripción corta de la skill B." in prompt
    assert "## Skills disponibles bajo demanda" in prompt
    # La skill siempre-on (skill-a) sigue concatenada tal cual, sin cambios.
    assert "Prompt de la skill A." in prompt


def test_skills_on_demand_quedan_en_config_body_para_la_tool(loader_env):
    """El contenido completo viaja en config_body['skills']['on_demand'] —
    de ahí lo lee la tool activar_skill en runtime."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija-on-demand")
    on_demand = result["config_body"]["skills"]["on_demand"]

    assert on_demand == {
        "skill-b": {
            "description": "Descripción corta de la skill B.",
            "prompt": "Prompt completo de la skill B.",
        }
    }


def test_activar_skill_se_agrega_a_tools_allow_solo_si_hay_on_demand(loader_env):
    from hub import specialty_loader

    con_on_demand = specialty_loader.resolve_specialty("hija-on-demand")
    sin_on_demand = specialty_loader.resolve_specialty("hija")

    assert "activar_skill" in con_on_demand["config_body"]["tools"]["allow"]
    assert "activar_skill" not in sin_on_demand["config_body"]["tools"]["allow"]


def test_skills_on_demand_tools_no_se_unen_a_tools_allow(loader_env):
    """A diferencia de las skills siempre-on, las on-demand NO le agregan
    sus propias tools a tools.allow — el modelo solo gana 'activar_skill';
    las tools reales de la skill deben venir del tools.allow explícito de
    la specialty si se necesitan (ver nota de diseño en specialty_loader)."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija-on-demand")
    assert "exec_command" not in result["config_body"]["tools"]["allow"]


def test_skills_on_demand_conocimiento_se_resuelve_igual_que_siempre_on(loader_env):
    """El conocimiento de una skill on-demand se copia igual — el RAG ya es
    progresivo por retrieval, no hace falta esperar a activar_skill."""
    from hub import specialty_loader

    result = specialty_loader.resolve_specialty("hija-on-demand")
    resolved_names = {p.name for p in result["knowledge_source_files"]}
    assert "de-la-skill-b.yaml" in resolved_names
