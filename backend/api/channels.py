"""Endpoints para gestión de canales (WhatsApp, Telegram…)."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@router.get("")
async def list_channels():
    from backend.channels.whatsapp import whatsapp
    wa_status = await whatsapp.status()
    return {
        "whatsapp": wa_status,
    }


@router.post("/whatsapp/connect")
async def connect_whatsapp(background_tasks: BackgroundTasks):
    from backend.channels.whatsapp import whatsapp
    background_tasks.add_task(whatsapp.connect)
    return {"ok": True, "message": "Conectando WhatsApp en segundo plano..."}


@router.get("/whatsapp/status")
async def whatsapp_status():
    from backend.channels.whatsapp import whatsapp
    return await whatsapp.status()


@router.get("/whatsapp/qr")
async def whatsapp_qr():
    from backend.channels.whatsapp import whatsapp
    status = await whatsapp.status()
    if status.get("connected"):
        return {"connected": True, "qr": None}
    qr = await whatsapp.get_qr()
    if not qr:
        return {"connected": False, "qr": None, "message": "Inicia la conexión primero"}
    return {"connected": False, "qr": qr}


@router.post("/whatsapp/disconnect")
async def disconnect_whatsapp():
    from backend.channels.whatsapp import whatsapp
    await whatsapp.stop()
    return {"ok": True}


class SendRequest(BaseModel):
    to: str
    message: str


@router.post("/whatsapp/send")
async def send_whatsapp(req: SendRequest):
    from backend.channels.whatsapp import whatsapp
    status = await whatsapp.status()
    if not status.get("connected"):
        raise HTTPException(503, "WhatsApp no conectado")
    await whatsapp.send(req.to, req.message)
    return {"ok": True}


@router.post("/whatsapp/incoming")
async def incoming_message(payload: dict):
    """Webhook llamado por el sidecar cuando llega un mensaje."""
    from backend.api.chat import process_message
    text = payload.get("text", "")
    sender = payload.get("sender", "")
    if not text or not sender:
        return {"ok": False}

    result = await process_message(
        message=text,
        session_id=None,
        user_id=sender,
        specialty_id="core",
    )

    from backend.channels.whatsapp import whatsapp
    await whatsapp.send(sender, result["reply"])
    return {"ok": True}
