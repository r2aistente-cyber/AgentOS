"""Conftest para tests de hub/templates.

Provee la fixture `template_env` que expone un agent_config falso y
hub/templates en sys.path (ver tests/_template_support.py) más una BD
SQLite inicializada en un directorio temporal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _template_support import (  # noqa: E402
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


@pytest.fixture(autouse=True)
def template_env(tmp_path):
    """Entorno aislado de agente para cualquier test en este directorio."""
    cfg = default_config(tmp_path)
    mod = install_agent_config(tmp_path, cfg)

    yield {
        "agent_dir": tmp_path,
        "data_dir": tmp_path / "data",
        "cfg": cfg,
        "mod": mod,
    }

    cleanup_template_modules()


@pytest_asyncio.fixture
async def db(template_env):
    """BD SQLite inicializada en el directorio del agente de test."""
    import memory.db as db_mod
    db_path = template_env["agent_dir"] / "memory.db"
    db_mod._DB_PATH = db_path
    from memory.db import init_db
    await init_db()
    yield db_path
