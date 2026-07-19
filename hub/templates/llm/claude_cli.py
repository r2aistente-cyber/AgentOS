"""Adapter Claude via CLI OAuth — usa el token de sesion de Claude Code/CLI
almacenado en ~/.claude/.credentials.json.

No requiere API key ni creditos: funciona con la suscripcion Pro activa.
Refresca el access token automaticamente cuando esta por vencer.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

import agent_config as config
from llm.adapter import LLMAdapter, LLMResponse, ToolCall

_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"
_API_URL = "https://api.anthropic.com/v1/messages"
_REFRESH_URL = "https://auth.anthropic.com/oauth/token"
_VERSION = "2023-06-01"
_MARGIN_MS = 5 * 60 * 1000  # refrescar 5 min antes de que expire


def _load_credentials() -> dict:
    if not _CREDENTIALS.exists():
        raise RuntimeError(
            f"No se encontraron credenciales de Claude CLI en {_CREDENTIALS}. "
            "Ejecuta 'claude' y autenticate primero."
        )
    return json.loads(_CREDENTIALS.read_text(encoding="utf-8"))


def _save_credentials(data: dict) -> None:
    _CREDENTIALS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _get_access_token() -> str:
    """Devuelve el access token vigente, refrescandolo si esta por expirar."""
    data = _load_credentials()
    oauth = data.get("claudeAiOauth", {})
    expires_at = oauth.get("expiresAt", 0)  # epoch ms

    if time.time() * 1000 < expires_at - _MARGIN_MS:
        return oauth["accessToken"]

    # Token expirado o por vencer — refrescar
    refresh_token = oauth.get("refreshToken")
    if not refresh_token:
        raise RuntimeError("No hay refreshToken disponible. Vuelve a autenticarte con 'claude'.")

    resp = httpx.post(
        _REFRESH_URL,
        json={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=15,
    )
    resp.raise_for_status()
    new_tokens = resp.json()

    oauth["accessToken"] = new_tokens["access_token"]
    oauth["expiresAt"] = int(time.time() * 1000) + new_tokens.get("expires_in", 3600) * 1000
    if "refresh_token" in new_tokens:
        oauth["refreshToken"] = new_tokens["refresh_token"]

    data["claudeAiOauth"] = oauth
    _save_credentials(data)
    return oauth["accessToken"]


class ClaudeCliAdapter(LLMAdapter):
    def __init__(self, model: str | None = None) -> None:
        self._model = model or config.get("llm.model", "claude-sonnet-4-6")
        self._temperature = config.get("llm.temperature", 0.7)
        self._max_tokens = config.get("llm.max_tokens", 4096)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {_get_access_token()}",
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }

    async def ping(self) -> bool:
        try:
            _get_access_token()
            return True
        except Exception:
            return False

    async def chat(self, messages, tools=None, system=None) -> LLMResponse:
        from llm.anthropic import _to_anthropic_messages, _to_anthropic_tools

        payload: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": _to_anthropic_messages(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = _to_anthropic_tools(tools)

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(_API_URL, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()

        text_parts, tool_calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    arguments=block.get("input", {}) or {},
                ))
        usage = data.get("usage", {})
        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
