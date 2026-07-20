"""Conftest para tests de hub/templates.

Provee la fixture `template_env` que:
  - Añade hub/templates/ al sys.path
  - Inyecta un agent_config falso apuntando a un directorio temporal
  - Inicializa la BD SQLite del agente en ese directorio
  - Limpia sys.modules al finalizar para no contaminar otras suites
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
import pytest_asyncio

_TEMPLATES = Path(__file__).resolve().parent.parent.parent / "hub" / "templates"


@pytest.fixture(autouse=True)
def template_env(tmp_path):
    """Entorno aislado de agente para cualquier test en este directorio."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    _cfg = {
        "agent": {
            "name": "template-test-agent",
            "port": 9998,
            "install_path": str(tmp_path),
        },
        "llm": {"provider": "mock", "model": "test-model", "num_ctx": 8192},
        "tools": {"allow": ["*"], "deny": []},
        "security": {
            "sandbox_paths": [str(data_dir)],
            "level": 1,
        },
        "memory": {},
    }

    def _get(key, default=None):
        node = _cfg
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    mod = types.ModuleType("agent_config")
    mod.get = _get
    mod.get_secret = lambda _: None
    mod.AGENT_DIR = tmp_path
    mod.reload = lambda: None
    sys.modules["agent_config"] = mod

    if str(_TEMPLATES) not in sys.path:
        sys.path.insert(0, str(_TEMPLATES))

    yield {
        "agent_dir": tmp_path,
        "data_dir": data_dir,
        "cfg": _cfg,
        "mod": mod,
    }

    sys.modules.pop("agent_config", None)
    for key in list(sys.modules):
        if key.startswith(("llm.", "tools.", "security.", "memory.", "rag.", "engine")):
            sys.modules.pop(key, None)
    for pkg in ("llm", "tools", "security", "memory", "rag", "engine"):
        mod_obj = sys.modules.get(pkg)
        if mod_obj is not None and not getattr(mod_obj, "__file__", None):
            sys.modules.pop(pkg, None)
    if str(_TEMPLATES) in sys.path:
        sys.path.remove(str(_TEMPLATES))


@pytest_asyncio.fixture
async def db(template_env):
    """BD SQLite inicializada en el directorio del agente de test."""
    import memory.db as db_mod
    db_path = template_env["agent_dir"] / "memory.db"
    db_mod._DB_PATH = db_path
    from memory.db import init_db
    await init_db()
    yield db_path
