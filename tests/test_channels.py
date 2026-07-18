"""Tests de canales: WhatsApp status, QR, send, webhook."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch


async def test_list_channels_retorna_estructura(client):
    r = await client.get("/api/v1/channels")
    assert r.status_code == 200
    body = r.json()
    assert "whatsapp" in body


async def test_whatsapp_status_no_conectado(client):
    r = await client.get("/api/v1/channels/whatsapp/status")
    assert r.status_code == 200
    body = r.json()
    assert "connected" in body
    assert body["connected"] is False


async def test_whatsapp_qr_sin_conectar(client):
    r = await client.get("/api/v1/channels/whatsapp/qr")
    assert r.status_code == 200
    body = r.json()
    assert "connected" in body
    assert body["connected"] is False


async def test_whatsapp_send_sin_conexion_da_503(client):
    r = await client.post("/api/v1/channels/whatsapp/send", json={"to": "+57300", "message": "Hola"})
    assert r.status_code == 503


async def test_whatsapp_disconnect(client):
    r = await client.post("/api/v1/channels/whatsapp/disconnect")
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_whatsapp_connect_en_background(client):
    r = await client.post("/api/v1/channels/whatsapp/connect")
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_incoming_webhook_sin_texto(client):
    """Webhook sin texto → ok=False, no crash."""
    r = await client.post("/api/v1/channels/whatsapp/incoming", json={"sender": "+57300", "text": ""})
    assert r.status_code == 200
    assert r.json()["ok"] is False


async def test_incoming_webhook_sin_sender(client):
    r = await client.post("/api/v1/channels/whatsapp/incoming", json={"sender": "", "text": "hola"})
    assert r.status_code == 200
    assert r.json()["ok"] is False


async def test_incoming_webhook_procesa_mensaje(client):
    """Webhook con mensaje válido llama process_message y responde."""
    mock_result = {
        "session_id": "test-sid",
        "reply": "Respuesta de prueba",
        "tools_used": [],
        "tokens": 10,
    }

    # process_message se importa dentro de la función con 'from backend.api.chat import ...'
    # por eso el patch va en el módulo origen, no en channels
    with patch("backend.api.chat.process_message", new_callable=AsyncMock, return_value=mock_result):
        r = await client.post(
            "/api/v1/channels/whatsapp/incoming",
            json={"sender": "+57300000000", "text": "¿Cuántas ventas hay?"},
        )
    assert r.status_code == 200
    assert r.json()["ok"] is True
