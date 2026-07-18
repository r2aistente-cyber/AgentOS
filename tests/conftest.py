"""Fixtures compartidos para toda la suite de tests.

Estrategia de aislamiento:
- DB temporal por sesión de pytest (/tmp/r2_test_<pid>.db)
- Config en memoria (sandbox apunta a /tmp)
- Cliente HTTP async via httpx + ASGITransport
- WhatsApp sidecar completamente mockeado
- Ollama nunca se llama en tests (mock via respx)
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ─── DB temporal ──────────────────────────────────────────────────────────────

_TMP_DB = Path(tempfile.gettempdir()) / f"r2_test_{os.getpid()}.db"


@pytest.fixture(scope="session", autouse=True)
def _patch_db_path():
    """Redirige la BD a /tmp para no tocar ~/.r2/memory.db real."""
    import backend.memory.db as db_mod
    original = db_mod._DB_PATH
    db_mod._DB_PATH = _TMP_DB
    yield
    db_mod._DB_PATH = original
    try:
        _TMP_DB.unlink()
    except OSError:
        pass


@pytest.fixture(scope="session", autouse=True)
def _patch_config():
    """Inyecta config de test: sandbox → /tmp, LLM deshabilitado."""
    test_cfg = {
        "hub": {"name": "AgentOS", "port": 8234},
        "llm": {
            "provider": "ollama",
            "model": "test-model",
            "host": "http://localhost:11434",
        },
        "security": {
            "sandbox_paths": ["/tmp/r2_test_sandbox/"],
        },
        "server": {"port": 8234},
        "channels": {"whatsapp": {"enabled": False}},
    }
    import backend.config as cfg_mod
    cfg_mod._load.cache_clear()
    with patch.object(cfg_mod, "_load", return_value=test_cfg):
        cfg_mod._load.cache_clear()
        yield
    cfg_mod._load.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _sandbox_dir():
    """Crea el directorio de sandbox de test."""
    d = Path("/tmp/r2_test_sandbox")
    d.mkdir(exist_ok=True)
    yield d


@pytest_asyncio.fixture(scope="session")
async def _init_db():
    """Inicializa la BD de test una sola vez."""
    from backend.memory.db import init_db
    await init_db()


@pytest_asyncio.fixture()
async def client(_patch_db_path, _patch_config, _init_db):
    """Cliente HTTP async para testear la app FastAPI."""
    _mock_wa = AsyncMock()
    _mock_wa.status = AsyncMock(return_value={"connected": False, "status": "disconnected"})
    _mock_wa.connect = AsyncMock()
    _mock_wa.stop = AsyncMock()
    _mock_wa.send = AsyncMock()
    _mock_wa.get_qr = AsyncMock(return_value=None)

    with patch("backend.channels.whatsapp.whatsapp", _mock_wa):
        from backend.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
