"""Herramientas de memoria a largo plazo."""
from __future__ import annotations

from backend.tools.registry import ToolDef, register


async def save_memory(key: str, value: str, category: str = "general") -> str:
    from backend.memory.db import get_db
    async with get_db() as db:
        await db.execute(
            """INSERT INTO long_term_memory (id, user_id, key, value, category)
               VALUES (lower(hex(randomblob(8))), 'xavier', ?, ?, ?)
               ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value,
               category=excluded.category, updated_at=CURRENT_TIMESTAMP""",
            (key, value, category),
        )
        await db.commit()
    return f"Guardado: {key} = {value[:80]}"


async def get_memory(key: str) -> str:
    from backend.memory.db import get_db
    async with get_db() as db:
        async with db.execute(
            "SELECT value FROM long_term_memory WHERE user_id='xavier' AND key=?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else f"No encontrado: {key}"


async def list_memories(category: str = "") -> str:
    from backend.memory.db import get_db
    query = "SELECT key, value, category FROM long_term_memory WHERE user_id='xavier'"
    params = []
    if category:
        query += " AND category=?"
        params.append(category)
    query += " ORDER BY updated_at DESC LIMIT 50"
    async with get_db() as db:
        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()
    if not rows:
        return "Sin memorias guardadas."
    return "\n".join(f"[{r[2]}] {r[0]}: {r[1][:80]}" for r in rows)


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="save_memory",
    description="Guarda un dato en la memoria a largo plazo del usuario.",
    category="memory",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Clave única del dato"},
            "value": {"type": "string", "description": "Valor a guardar"},
            "category": {"type": "string", "description": "Categoría: preference, fact, context", "default": "general"},
        },
        "required": ["key", "value"],
    },
    handler=save_memory,
))

register(ToolDef(
    name="get_memory",
    description="Recupera un dato de la memoria a largo plazo.",
    category="memory",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Clave a buscar"}},
        "required": ["key"],
    },
    handler=get_memory,
))

register(ToolDef(
    name="list_memories",
    description="Lista todos los datos guardados en la memoria a largo plazo.",
    category="memory",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {"category": {"type": "string", "description": "Filtrar por categoría (opcional)", "default": ""}},
    },
    handler=list_memories,
))
