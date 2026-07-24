"""Tests de AgentManager: creación y sincronización de código desde template.

Aislamiento: hub.config.templates_dir/agents_dir/registry_path/port_range
apuntan a tmp_path — nunca se toca ~/AgentOS real.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def manager_env(tmp_path):
    """Template mínimo + agents_dir/registry_path/port_range en tmp_path."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "default_config.yaml").write_text(
        "llm:\n  provider: mock\n  model: test\n", encoding="utf-8"
    )
    (templates / "engine.py").write_text("VERSION = 1\n", encoding="utf-8")
    tools_dir = templates / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    registry_path = tmp_path / "agents.json"

    import hub.config as cfg
    with patch.object(cfg, "templates_dir", return_value=templates), \
         patch.object(cfg, "agents_dir", return_value=agents_dir), \
         patch.object(cfg, "registry_path", return_value=registry_path), \
         patch.object(cfg, "port_range", return_value=(9000, 9010)):
        yield {"templates": templates, "agents_dir": agents_dir}


def test_create_copia_el_template(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    info = mgr.create("agente1", {})
    agent_dir = Path(info.dir)

    assert (agent_dir / "engine.py").read_text(encoding="utf-8") == "VERSION = 1\n"
    assert (agent_dir / "tools" / "__init__.py").exists()
    assert (agent_dir / "config.yaml").exists()


def test_sync_from_template_actualiza_codigo_sin_tocar_config_ni_data(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    info = mgr.create("agente2", {})
    agent_dir = Path(info.dir)

    # El usuario "customizó" su config y tiene datos propios en el workspace.
    (agent_dir / "config.yaml").write_text("custom: true\n", encoding="utf-8")
    (agent_dir / "data").mkdir(exist_ok=True)
    (agent_dir / "data" / "mio.txt").write_text("no tocar", encoding="utf-8")

    # El template se actualiza (simula un fix como los de esta sesión).
    (manager_env["templates"] / "engine.py").write_text("VERSION = 2\n", encoding="utf-8")

    mgr.sync_from_template("agente2")

    assert (agent_dir / "engine.py").read_text(encoding="utf-8") == "VERSION = 2\n"
    assert (agent_dir / "config.yaml").read_text(encoding="utf-8") == "custom: true\n"
    assert (agent_dir / "data" / "mio.txt").read_text(encoding="utf-8") == "no tocar"


def test_sync_from_template_agente_inexistente_da_keyerror(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    with pytest.raises(KeyError):
        mgr.sync_from_template("no_existe")


def test_sync_from_template_agrega_archivos_nuevos_del_template(manager_env):
    """Si el template ganó un archivo/paquete nuevo desde que se creó el
    agente, sync también lo copia (no solo actualiza los que ya existían)."""
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    mgr.create("agente3", {})

    (manager_env["templates"] / "rag").mkdir()
    (manager_env["templates"] / "rag" / "__init__.py").write_text("", encoding="utf-8")

    info = mgr.sync_from_template("agente3")
    assert (Path(info.dir) / "rag" / "__init__.py").exists()
