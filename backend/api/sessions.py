"""Endpoints de sesiones."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.memory import session as store

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


class NewSessionRequest(BaseModel):
    user_id: str = "xavier"
    specialty_id: str = "core"
    title: str = "Nueva sesión"


@router.get("")
async def list_sessions(user_id: str = "xavier", limit: int = 20):
    return await store.list_sessions(user_id, limit)


@router.post("/new")
async def new_session(req: NewSessionRequest):
    sid = await store.create_session(req.user_id, req.specialty_id, req.title)
    return {"session_id": sid}


@router.get("/{session_id}")
async def get_session(session_id: str):
    s = await store.get_session(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    history = await store.get_history(session_id, limit=100)
    return {"session": s, "messages": history}


@router.delete("/{session_id}")
async def archive_session(session_id: str):
    s = await store.get_session(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    await store.archive_session(session_id)
    return {"ok": True}
