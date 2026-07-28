"""Tests de tools/base_tools/skill_tools.py (activar_skill).

Carga bajo demanda de skills: el contenido completo vive en
config['skills']['on_demand'][nombre]['prompt'] (puesto ahí por
hub/specialty_loader.py) — esta tool solo lo expone al runtime del agente.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_activar_skill_devuelve_el_prompt_completo(template_env):
    template_env["cfg"]["skills"] = {
        "on_demand": {
            "asistente-escritura": {
                "description": "Redactar y corregir textos",
                "prompt": "Instrucciones completas de escritura.",
            }
        }
    }

    from tools.base_tools.skill_tools import activar_skill
    resultado = await activar_skill("asistente-escritura")

    assert resultado == "Instrucciones completas de escritura."


@pytest.mark.asyncio
async def test_activar_skill_inexistente_lista_las_disponibles(template_env):
    template_env["cfg"]["skills"] = {
        "on_demand": {
            "asistente-escritura": {"description": "x", "prompt": "y"},
            "lectura-documentos": {"description": "x", "prompt": "y"},
        }
    }

    from tools.base_tools.skill_tools import activar_skill
    resultado = await activar_skill("skill-que-no-existe")

    assert "no existe" in resultado
    assert "asistente-escritura" in resultado
    assert "lectura-documentos" in resultado


@pytest.mark.asyncio
async def test_activar_skill_sin_ninguna_configurada(template_env):
    """Sin skills.on_demand en config (agente sin specialty con on-demand),
    no debe crashear — reporta que no hay ninguna disponible."""
    from tools.base_tools.skill_tools import activar_skill
    resultado = await activar_skill("cualquiera")

    assert "no existe" in resultado
    assert "(ninguna)" in resultado
