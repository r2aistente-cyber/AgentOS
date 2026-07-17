"""Endpoints de administración: auditoría, usuarios, permisos."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.memory.db import get_db

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/audit")
async def get_audit(user_id: str = "", tool_name: str = "", limit: int = 50):
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if user_id:
        query += " AND user_id=?"
        params.append(user_id)
    if tool_name:
        query += " AND tool_name=?"
        params.append(tool_name)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    async with get_db() as db:
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.get("/users")
async def list_users():
    async with get_db() as db:
        async with db.execute("SELECT id, name, role, permission_level, created_at, active FROM users") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


class UserUpsert(BaseModel):
    id: str
    name: str
    role: str = "user"
    permission_level: int = 1


@router.post("/users")
async def upsert_user(req: UserUpsert):
    if req.permission_level not in (0, 1, 2, 3):
        raise HTTPException(400, "permission_level debe ser 0-3")
    async with get_db() as db:
        await db.execute(
            """INSERT INTO users (id, name, role, permission_level)
               VALUES (?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name,
               role=excluded.role, permission_level=excluded.permission_level""",
            (req.id, req.name, req.role, req.permission_level),
        )
        await db.commit()
    return {"ok": True, "user_id": req.id}


class PermissionUpdate(BaseModel):
    user_id: str
    level: int


@router.post("/permissions")
async def set_permission(req: PermissionUpdate):
    if req.level not in (0, 1, 2, 3):
        raise HTTPException(400, "level debe ser 0-3")
    async with get_db() as db:
        await db.execute(
            "UPDATE users SET permission_level=? WHERE id=?",
            (req.level, req.user_id),
        )
        await db.commit()
    return {"ok": True}
