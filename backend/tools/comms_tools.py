"""Herramientas de comunicación: WhatsApp, etc. (Fase 4)."""
from __future__ import annotations

from backend.tools.registry import ToolDef, register


async def _send_whatsapp(to: str, message: str) -> str:
    from backend.channels.whatsapp import whatsapp
    status = await whatsapp.status()
    if not status.get("connected"):
        return "Error: WhatsApp no está conectado. Usa el endpoint /api/v1/channels/whatsapp/connect primero."
    await whatsapp.send(to, message)
    return f"Mensaje enviado a {to}."


register(ToolDef(
    name="send_whatsapp",
    description="Envía un mensaje de WhatsApp al número o chat indicado.",
    category="comms",
    min_level=2,
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Número de teléfono (ej: 573192270876) o chat_id con @c.us / @g.us",
            },
            "message": {
                "type": "string",
                "description": "Texto del mensaje a enviar",
            },
        },
        "required": ["to", "message"],
    },
    handler=_send_whatsapp,
    requires_confirmation=True,
))
