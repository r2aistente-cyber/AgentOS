"""Tests del canal de Telegram (hub/templates/telegram_bot.py).

A diferencia de WhatsApp no hay sidecar Node — todo corre como long-polling
dentro del proceso del agente. httpx se mockea siempre, nunca se pega a la
Bot API real. engine.process_message se mockea vía monkeypatch para no
depender de un LLM real (igual que test_engine_e2e.py).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ─── Helpers puros ────────────────────────────────────────────────────────────

def test_get_token_ausente_por_defecto(template_env):
    from telegram_bot import _get_token
    assert _get_token() is None


def test_get_token_lee_config(template_env):
    template_env["cfg"]["channels"] = {"telegram": {"bot_token": "123:ABC"}}
    from telegram_bot import _get_token
    assert _get_token() == "123:ABC"


def test_is_allowed_sin_whitelist_permite_todo():
    from telegram_bot import _is_allowed
    assert _is_allowed(999, []) is True


def test_is_allowed_con_whitelist_filtra():
    from telegram_bot import _is_allowed
    assert _is_allowed(111, ["111", "222"]) is True
    assert _is_allowed(333, ["111", "222"]) is False


# ─── run_telegram_polling: sin token no debe entrar al loop ──────────────────

@pytest.mark.asyncio
async def test_run_telegram_polling_sin_token_retorna_de_inmediato(template_env):
    """Si esto no retornara de inmediato, el test colgaría (loop infinito)
    hasta que pytest-asyncio lo mate por timeout — no hay token configurado
    en la config de test, así que run_telegram_polling debe salir apenas
    entra, sin llamar a la Bot API."""
    from telegram_bot import run_telegram_polling
    await run_telegram_polling()


# ─── _handle_update ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_handle_update_ignora_chat_no_autorizado(template_env, monkeypatch):
    import engine
    from telegram_bot import _handle_update

    mock_process = AsyncMock(return_value={"reply": "no debería llamarse"})
    monkeypatch.setattr(engine, "process_message", mock_process)
    client = MagicMock()
    client.post = AsyncMock()
    upd = {"update_id": 1, "message": {"chat": {"id": 999}, "text": "hola"}}

    await _handle_update(client, "tok", ["111"], upd)

    mock_process.assert_not_called()
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_handle_update_ignora_mensaje_sin_texto(template_env, monkeypatch):
    import engine
    from telegram_bot import _handle_update

    mock_process = AsyncMock()
    monkeypatch.setattr(engine, "process_message", mock_process)
    client = MagicMock()
    client.post = AsyncMock()
    upd = {"update_id": 1, "message": {"chat": {"id": 111}, "sticker": {}}}

    await _handle_update(client, "tok", [], upd)

    mock_process.assert_not_called()
    client.post.assert_not_called()


@pytest.mark.asyncio
async def test_handle_update_reenvia_al_engine_y_responde(template_env, monkeypatch):
    import engine
    from telegram_bot import _handle_update

    mock_process = AsyncMock(return_value={"reply": "Hola, soy el agente"})
    monkeypatch.setattr(engine, "process_message", mock_process)
    client = MagicMock()
    client.post = AsyncMock()
    upd = {"update_id": 1, "message": {"chat": {"id": 111}, "text": "hola agente"}}

    await _handle_update(client, "tok123", ["111"], upd)

    # chat_id 111 se usa como session_id Y user_id, mismo patrón que el
    # sidecar de WhatsApp con el número de teléfono.
    mock_process.assert_awaited_once_with("hola agente", "telegram:111", "telegram:111", None)
    client.post.assert_awaited_once()
    args, kwargs = client.post.call_args
    assert "tok123" in args[0]
    assert kwargs["json"]["chat_id"] == 111
    assert kwargs["json"]["text"] == "Hola, soy el agente"


@pytest.mark.asyncio
async def test_handle_update_error_en_engine_no_crashea(template_env, monkeypatch):
    import engine
    from telegram_bot import _handle_update

    mock_process = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(engine, "process_message", mock_process)
    client = MagicMock()
    client.post = AsyncMock()
    upd = {"update_id": 1, "message": {"chat": {"id": 111}, "text": "hola"}}

    await _handle_update(client, "tok", [], upd)  # no debe lanzar

    client.post.assert_awaited_once()
    assert "error" in client.post.call_args.kwargs["json"]["text"].lower()


# ─── _send ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_trunca_mensajes_largos_en_varios_posts(template_env):
    from telegram_bot import _send, _MAX_MSG_CHARS
    client = MagicMock()
    client.post = AsyncMock()
    texto = "x" * (_MAX_MSG_CHARS + 100)

    await _send(client, "tok", 111, texto)

    assert client.post.await_count == 2
