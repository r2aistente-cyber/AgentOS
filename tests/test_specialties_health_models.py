"""Tests de specialties, health y models."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import respx
import httpx


# ═══════════════════════════════════════════════════════════════
#  SPECIALTIES
# ═══════════════════════════════════════════════════════════════

async def test_list_specialties_retorna_lista(client):
    r = await client.get("/api/v1/specialties")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_list_specialties_tiene_core(client):
    r = await client.get("/api/v1/specialties")
    ids = [s["id"] for s in r.json()]
    assert "core" in ids


async def test_get_specialty_core(client):
    r = await client.get("/api/v1/specialties/core")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "core"
    assert "personality" in body
    assert "tools" in body


async def test_get_specialty_inexistente_da_404(client):
    r = await client.get("/api/v1/specialties/no_existe_xyzabc")
    assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════════════════════

async def test_health_sin_ollama_degraded(client):
    """Sin Ollama, /health retorna degraded pero no falla con 500."""
    with patch("backend.llm.ollama.OllamaAdapter.ping", new_callable=AsyncMock, return_value=False):
        r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["llm"] is False


async def test_health_con_ollama_ok(client):
    with patch("backend.llm.ollama.OllamaAdapter.ping", new_callable=AsyncMock, return_value=True):
        r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["llm"] is True


# ═══════════════════════════════════════════════════════════════
#  MODELS
# ═══════════════════════════════════════════════════════════════

async def test_get_active_model(client):
    r = await client.get("/api/v1/models/active")
    assert r.status_code == 200
    body = r.json()
    assert "provider" in body
    assert "model" in body
    assert "host" in body


async def test_list_models_sin_ollama_da_503(client):
    with respx.mock:
        respx.get("http://localhost:11434/api/tags").mock(side_effect=httpx.ConnectError("no Ollama"))
        r = await client.get("/api/v1/models")
    assert r.status_code == 503


async def test_list_models_con_ollama_mock(client):
    mock_response = httpx.Response(200, json={"models": [
        {"name": "qwen2.5:latest", "size": 1000000, "modified_at": "2026-01-01"},
        {"name": "deepseek:7b", "size": 2000000, "modified_at": "2026-01-02"},
    ]})
    with respx.mock:
        respx.get("http://localhost:11434/api/tags").mock(return_value=mock_response)
        r = await client.get("/api/v1/models")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2
    names = [m["name"] for m in data]
    assert "qwen2.5:latest" in names
