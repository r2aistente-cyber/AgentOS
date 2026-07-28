"""Tests de GET /api/v1/models — el selector de modelo del chat depende de
que el modelo primario (llm.provider/model) SIEMPRE aparezca en la lista,
aunque `llm.models` haya quedado desactualizada (ej. se cambió provider/
model a mano en la página de edición del agente sin tocar esa lista —
bug real reportado por Xavier: cambió a opencode-go/deepseek-v4-pro pero
el selector del chat seguía mostrando solo el modelo viejo)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _template_support import (  # noqa: E402
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


async def _get_models(tmp_path, llm_overrides: dict) -> dict:
    cfg = default_config(tmp_path)
    cfg["llm"].update(llm_overrides)
    install_agent_config(tmp_path, cfg)
    try:
        import agent_main
        async with AsyncClient(transport=ASGITransport(app=agent_main.app), base_url="http://test") as c:
            resp = await c.get("/api/v1/models")
            assert resp.status_code == 200, resp.text
            return resp.json()
    finally:
        cleanup_template_modules()


@pytest.mark.asyncio
async def test_primario_se_sintetiza_si_no_hay_lista_models(tmp_path):
    data = await _get_models(tmp_path, {"provider": "ollama", "model": "qwen2.5:latest"})
    assert data["default"] == "ollama/qwen2.5:latest"
    assert [m["ref"] for m in data["models"]] == ["ollama/qwen2.5:latest"]


@pytest.mark.asyncio
async def test_primario_ausente_de_una_lista_desactualizada_se_antepone(tmp_path):
    """Reproduce el bug: llm.models trae solo la entrada vieja (qwen2.5) pero
    provider/model ya se cambiaron a opencode-go/deepseek-v4-pro — el
    selector debe poder mostrar y elegir el modelo realmente activo."""
    data = await _get_models(tmp_path, {
        "provider": "opencode-go",
        "model": "deepseek-v4-pro",
        "models": [{"provider": "ollama", "model": "qwen2.5:latest", "label": "Qwen 2.5"}],
    })

    assert data["default"] == "opencode-go/deepseek-v4-pro"
    refs = [m["ref"] for m in data["models"]]
    assert "opencode-go/deepseek-v4-pro" in refs
    assert "ollama/qwen2.5:latest" in refs  # la vieja se conserva como opción


@pytest.mark.asyncio
async def test_primario_ya_incluido_no_se_duplica(tmp_path):
    data = await _get_models(tmp_path, {
        "provider": "opencode-go",
        "model": "deepseek-v4-pro",
        "models": [
            {"provider": "opencode-go", "model": "deepseek-v4-pro", "label": "DeepSeek V4 Pro"},
            {"provider": "ollama", "model": "qwen2.5:latest", "label": "Qwen 2.5"},
        ],
    })

    refs = [m["ref"] for m in data["models"]]
    assert refs.count("opencode-go/deepseek-v4-pro") == 1
    # Se conserva el label explícito de la entrada existente, no se sobreescribe
    primary = next(m for m in data["models"] if m["ref"] == "opencode-go/deepseek-v4-pro")
    assert primary["label"] == "DeepSeek V4 Pro"
