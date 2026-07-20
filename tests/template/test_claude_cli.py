"""Tests del adapter Claude CLI OAuth (hub/templates/llm/claude_cli.py).

No se hacen llamadas reales a la API de Anthropic — todo es mockeado.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─── _load_credentials ────────────────────────────────────────────────────────

def test_load_credentials_sin_archivo(tmp_path, template_env):
    from llm.claude_cli import _load_credentials
    fake_creds = tmp_path / ".credentials.json"

    with patch("llm.claude_cli._CREDENTIALS", fake_creds):
        with pytest.raises(RuntimeError, match="credenciales"):
            _load_credentials()


def test_load_credentials_con_archivo(tmp_path, template_env):
    from llm.claude_cli import _load_credentials
    fake_creds = tmp_path / ".credentials.json"
    data = {"claudeAiOauth": {"accessToken": "tok123", "expiresAt": 9999999999999}}
    fake_creds.write_text(json.dumps(data), encoding="utf-8")

    with patch("llm.claude_cli._CREDENTIALS", fake_creds):
        result = _load_credentials()

    assert result["claudeAiOauth"]["accessToken"] == "tok123"


# ─── _get_access_token: token vigente ─────────────────────────────────────────

def test_get_access_token_vigente(tmp_path, template_env):
    """Si el token no ha vencido, se retorna sin refrescar."""
    from llm.claude_cli import _get_access_token
    fake_creds = tmp_path / ".credentials.json"
    # expiresAt en el futuro lejano (epoch ms)
    expires_at = int(time.time() * 1000) + 60 * 60 * 1000  # 1h en el futuro
    data = {"claudeAiOauth": {"accessToken": "valid_token", "expiresAt": expires_at}}
    fake_creds.write_text(json.dumps(data), encoding="utf-8")

    with patch("llm.claude_cli._CREDENTIALS", fake_creds):
        token = _get_access_token()

    assert token == "valid_token"


# ─── _get_access_token: token expirado → refresca ─────────────────────────────

def test_get_access_token_expirado_refresca(tmp_path, template_env):
    """Si el token venció, debe hacer POST al endpoint de refresh."""
    from llm.claude_cli import _get_access_token
    fake_creds = tmp_path / ".credentials.json"
    # expiresAt en el pasado
    expires_at = int(time.time() * 1000) - 1000
    data = {
        "claudeAiOauth": {
            "accessToken": "old_token",
            "expiresAt": expires_at,
            "refreshToken": "refresh_tok",
        }
    }
    fake_creds.write_text(json.dumps(data), encoding="utf-8")

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_token",
        "expires_in": 3600,
    }

    with patch("llm.claude_cli._CREDENTIALS", fake_creds), \
         patch("httpx.post", return_value=mock_response) as mock_post:
        token = _get_access_token()

    mock_post.assert_called_once()
    assert token == "new_token"
    # Las credenciales actualizadas deben guardarse
    saved = json.loads(fake_creds.read_text())
    assert saved["claudeAiOauth"]["accessToken"] == "new_token"


def test_get_access_token_sin_refresh_token_lanza_error(tmp_path, template_env):
    """Sin refreshToken, lanza RuntimeError con mensaje claro."""
    from llm.claude_cli import _get_access_token
    fake_creds = tmp_path / ".credentials.json"
    expires_at = int(time.time() * 1000) - 1000
    data = {"claudeAiOauth": {"accessToken": "old", "expiresAt": expires_at}}
    fake_creds.write_text(json.dumps(data), encoding="utf-8")

    with patch("llm.claude_cli._CREDENTIALS", fake_creds):
        with pytest.raises(RuntimeError, match="refreshToken"):
            _get_access_token()


# ─── ClaudeCliAdapter.ping ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ping_token_valido(tmp_path, template_env):
    from llm.claude_cli import ClaudeCliAdapter
    with patch("llm.claude_cli._get_access_token", return_value="tok"):
        adapter = ClaudeCliAdapter()
        result = await adapter.ping()
    assert result is True


@pytest.mark.asyncio
async def test_ping_sin_credenciales(tmp_path, template_env):
    from llm.claude_cli import ClaudeCliAdapter
    with patch("llm.claude_cli._get_access_token", side_effect=RuntimeError("no credentials")):
        adapter = ClaudeCliAdapter()
        result = await adapter.ping()
    assert result is False


# ─── ClaudeCliAdapter.chat ────────────────────────────────────────────────────

def _make_async_client(mock_http_resp):
    """Crea un mock de httpx.AsyncClient que funciona como async context manager."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_http_resp)
    # async with httpx.AsyncClient() as client → __aenter__ retorna el client
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_chat_retorna_respuesta_texto(tmp_path, template_env):
    from llm.claude_cli import ClaudeCliAdapter
    from llm.adapter import LLMResponse

    mock_api_response = {
        "content": [{"type": "text", "text": "Respuesta de Claude."}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }

    mock_http_resp = MagicMock()
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_resp.json.return_value = mock_api_response

    with patch("llm.claude_cli._get_access_token", return_value="valid_tok"), \
         patch("httpx.AsyncClient", return_value=_make_async_client(mock_http_resp)):
        adapter = ClaudeCliAdapter(model="claude-sonnet-4-6")
        result = await adapter.chat([{"role": "user", "content": "hola"}])

    assert isinstance(result, LLMResponse)
    assert result.content == "Respuesta de Claude."
    assert result.output_tokens == 5


@pytest.mark.asyncio
async def test_chat_retorna_tool_calls(tmp_path, template_env):
    from llm.claude_cli import ClaudeCliAdapter

    mock_api_response = {
        "content": [
            {"type": "tool_use", "id": "tc1", "name": "list_files", "input": {"path": "."}}
        ],
        "usage": {"input_tokens": 15, "output_tokens": 8},
    }

    mock_http_resp = MagicMock()
    mock_http_resp.raise_for_status = MagicMock()
    mock_http_resp.json.return_value = mock_api_response

    with patch("llm.claude_cli._get_access_token", return_value="tok"), \
         patch("httpx.AsyncClient", return_value=_make_async_client(mock_http_resp)):
        adapter = ClaudeCliAdapter()
        result = await adapter.chat([{"role": "user", "content": "lista archivos"}])

    assert result.has_tool_calls
    assert result.tool_calls[0].name == "list_files"
    assert result.tool_calls[0].arguments == {"path": "."}
