"""CRUD de sesiones y mensajes."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from backend.memory.db import get_db


async def create_session(user_id: str, specialty_id: str = "core", title: str = "Nueva sesión") -> str:
    sid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            "INSERT INTO sessions (id, user_id, specialty_id, title) VALUES (?,?,?,?)",
            (sid, user_id, specialty_id, title),
        )
        await db.commit()
    return sid


async def get_session(session_id: str) -> dict | None:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions WHERE id=? AND archived=0", (session_id,)
        ) as cur:
            row = await cur.fetchone()
    return dict(row) if row else None


async def list_sessions(user_id: str, limit: int = 20) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM sessions WHERE user_id=? AND archived=0 ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def archive_session(session_id: str) -> None:
    async with get_db() as db:
        await db.execute("UPDATE sessions SET archived=1 WHERE id=?", (session_id,))
        await db.commit()


async def add_message(
    session_id: str,
    role: str,
    content: str,
    tools_used: list[str] | None = None,
    tokens: int = 0,
) -> None:
    mid = str(uuid.uuid4())
    tools_json = json.dumps(tools_used) if tools_used else None
    async with get_db() as db:
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, tools_used, tokens) VALUES (?,?,?,?,?,?)",
            (mid, session_id, role, content, tools_json, tokens),
        )
        await db.commit()


async def get_history(session_id: str, limit: int = 30) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ) as cur:
            rows = await cur.fetchall()
    # Devolver en orden cronológico
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
