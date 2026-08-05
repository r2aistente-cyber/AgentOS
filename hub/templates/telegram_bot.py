"""Canal de Telegram — long polling, sin dependencias además de httpx.

A diferencia de WhatsApp (que necesita el sidecar Node de whatsapp-web.js
gestionado por el Hub, ver hub/whatsapp_manager.py), Telegram solo requiere
hablar HTTP con la Bot API — no hace falta un proceso separado ni un sidecar.
Por eso este módulo corre DENTRO del propio proceso del agente, como una
tarea de fondo arrancada en el lifespan de agent_main.py si
`channels.telegram.enabled` es true.

Cada chat de Telegram se mapea 1:1 a una sesión propia (`telegram:{chat_id}`)
pasada como session_id Y user_id a engine.process_message — mismo patrón que
usa el sidecar de WhatsApp con el número de teléfono (ver sidecar.js,
forwardToAgent). No hace falta tabla de sesiones aparte: session_store trata
ese string como id estable y arrastra el historial solo.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

import agent_config as config

log = logging.getLogger("agent.telegram")

_API = "https://api.telegram.org/bot{token}/{method}"
_MAX_MSG_CHARS = 4096  # límite duro de Telegram por mensaje
_POLL_TIMEOUT = 30     # long-poll: el GET espera hasta N s por updates nuevos
_RETRY_DELAY = 5       # espera tras un error de red/API antes de reintentar


def _get_token() -> str | None:
    return config.get("channels.telegram.bot_token") or None


def _get_allowed() -> list[str]:
    return [str(u) for u in (config.get("channels.telegram.allowed_users") or [])]


def _is_allowed(chat_id: int, allowed: list[str]) -> bool:
    # Sin whitelist configurada = abierto a cualquiera. Se permite a propósito
    # (por si alguien quiere un bot público), pero agent_config lo deja
    # explícito en el config.yaml (allowed_users: []) para que no sea el
    # default silencioso.
    if not allowed:
        return True
    return str(chat_id) in allowed


async def _send(client: httpx.AsyncClient, token: str, chat_id: int, text: str) -> None:
    for i in range(0, len(text), _MAX_MSG_CHARS):
        try:
            await client.post(
                _API.format(token=token, method="sendMessage"),
                json={"chat_id": chat_id, "text": text[i : i + _MAX_MSG_CHARS]},
            )
        except Exception:
            log.exception("Fallo enviando mensaje a Telegram (chat_id=%s)", chat_id)


async def _handle_update(client: httpx.AsyncClient, token: str, allowed: list[str], upd: dict) -> None:
    from engine import process_message

    msg = upd.get("message") or upd.get("edited_message")
    if not msg or "text" not in msg:
        return  # ignora no-texto (fotos, stickers, etc.) por ahora

    chat_id = msg["chat"]["id"]
    if not _is_allowed(chat_id, allowed):
        log.warning("Mensaje de Telegram ignorado — chat_id no autorizado: %s", chat_id)
        return

    session_id = f"telegram:{chat_id}"
    try:
        result = await process_message(msg["text"], session_id, session_id, None)
        reply = result.get("reply", "")
    except Exception:
        log.exception("Error procesando mensaje de Telegram (chat_id=%s)", chat_id)
        reply = "⚠️ Tuve un error procesando tu mensaje."

    if reply:
        await _send(client, token, chat_id, reply)


async def run_telegram_polling() -> None:
    """Loop infinito de long-polling. Pensado para arrancar como
    asyncio.create_task() en el lifespan — nunca retorna en operación normal.
    """
    token = _get_token()
    if not token:
        log.warning("channels.telegram.enabled=true pero falta channels.telegram.bot_token — polling no arranca")
        return

    allowed = _get_allowed()
    if not allowed:
        log.warning("channels.telegram sin allowed_users — el bot responderá a cualquiera que le escriba")

    offset = 0
    log.info("Telegram polling iniciado")
    async with httpx.AsyncClient(timeout=_POLL_TIMEOUT + 10) as client:
        while True:
            try:
                r = await client.get(
                    _API.format(token=token, method="getUpdates"),
                    params={"offset": offset, "timeout": _POLL_TIMEOUT},
                )
                r.raise_for_status()
                updates = r.json().get("result", [])
            except Exception:
                log.exception("Error en getUpdates — reintentando en %ss", _RETRY_DELAY)
                await asyncio.sleep(_RETRY_DELAY)
                continue

            for upd in updates:
                offset = upd["update_id"] + 1
                await _handle_update(client, token, allowed, upd)
