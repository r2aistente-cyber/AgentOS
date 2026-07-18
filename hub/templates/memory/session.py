"""CRUD de sesiones y mensajes del agente."""
from __future__ import annotations

import json
import uuid

from memory.db import get_db


async def create_session(user_id: str, title: str = "Nueva sesión") -> str:
    sid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute("INSERT INTO sessions (id, user_id, title) VALUES (?,?,?)",
                         (sid, user_id, title))
        await db.commit()
    return sid


async def list_sessions(user_id: str, limit: int = 20) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT id, title, created_at FROM sessions WHERE user_id=? AND archived=0 "
            "ORDER BY created_at DESC LIMIT ?", (user_id, limit)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_message(session_id, role, content, tools_used=None, tokens=0) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT INTO messages (id, session_id, role, content, tools_used, tokens) "
            "VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), session_id, role, content,
             json.dumps(tools_used) if tools_used else None, tokens))
        await db.commit()


async def get_history(session_id, limit: int = 30) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY rowid DESC LIMIT ?",
            (session_id, limit)) as cur:
            rows = await cur.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def get_messages(session_id, limit: int = 200) -> list[dict]:
    """Historial completo de una sesión para reconstruir el chat en la UI (#6)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT role, content, tools_used, tokens FROM messages "
            "WHERE session_id=? ORDER BY rowid ASC LIMIT ?", (session_id, limit)) as cur:
            rows = await cur.fetchall()
    out = []
    for r in rows:
        out.append({
            "role": r["role"],
            "content": r["content"],
            "tools_used": json.loads(r["tools_used"]) if r["tools_used"] else [],
            "tokens": r["tokens"] or 0,
        })
    return out


async def archive_session(session_id) -> None:
    async with get_db() as db:
        await db.execute("UPDATE sessions SET archived=1 WHERE id=?", (session_id,))
        await db.commit()
