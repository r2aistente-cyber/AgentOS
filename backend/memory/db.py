"""SQLite init y context manager."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

_DB_PATH = Path.home() / ".r2" / "memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    specialty_id TEXT DEFAULT 'core',
    title       TEXT DEFAULT 'Nueva sesión',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      INTEGER DEFAULT 1,
    archived    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    tools_used  TEXT,
    tokens      INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS long_term_memory (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    category    TEXT DEFAULT 'general',
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT DEFAULT 'user',
    permission_level INTEGER DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS specialties (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    version     TEXT DEFAULT '1.0',
    config      TEXT NOT NULL,
    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    session_id  TEXT,
    tool_name   TEXT NOT NULL,
    params      TEXT,
    result      TEXT,
    success     INTEGER,
    duration_ms INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(SCHEMA)
        # Usuario Xavier por defecto
        await db.execute(
            """INSERT OR IGNORE INTO users (id, name, role, permission_level)
               VALUES ('xavier', 'Xavier', 'admin', 3)"""
        )
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db
