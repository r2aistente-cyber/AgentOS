"""Tools de memoria a largo plazo del agente."""
from __future__ import annotations

from tools.registry import ToolDef, register


async def save_memory(key: str, value: str, category: str = "general") -> str:
    from memory.db import get_db
    async with get_db() as db:
        await db.execute(
            """INSERT INTO long_term_memory (id, key, value, category)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,
               category=excluded.category, updated_at=CURRENT_TIMESTAMP""",
            (key, value, category))
        await db.commit()
    return f"Guardado: {key}"


async def get_memory(key: str) -> str:
    from memory.db import get_db
    async with get_db() as db:
        async with db.execute("SELECT value FROM long_term_memory WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else f"No encontrado: {key}"


async def list_memories(category: str = "") -> str:
    from memory.db import get_db
    q = "SELECT key, value, category FROM long_term_memory"
    params: list = []
    if category:
        q += " WHERE category=?"
        params.append(category)
    q += " ORDER BY updated_at DESC LIMIT 50"
    async with get_db() as db:
        async with db.execute(q, params) as cur:
            rows = await cur.fetchall()
    if not rows:
        return "Sin memorias guardadas."
    return "\n".join(f"[{r[2]}] {r[0]}: {r[1][:80]}" for r in rows)


register(ToolDef("save_memory", "Guarda un dato en la memoria a largo plazo.", "memory",
    {"type": "object", "properties": {
        "key": {"type": "string"}, "value": {"type": "string"},
        "category": {"type": "string", "default": "general"}},
     "required": ["key", "value"]}, save_memory))

register(ToolDef("get_memory", "Recupera un dato de la memoria a largo plazo.", "memory",
    {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
    get_memory))

register(ToolDef("list_memories", "Lista los datos guardados en memoria.", "memory",
    {"type": "object", "properties": {"category": {"type": "string", "default": ""}}},
    list_memories))
