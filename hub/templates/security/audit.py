"""Log de auditoría — solo append, nunca rompe el flujo principal."""
from __future__ import annotations

import asyncio
import json
from typing import Any


class AuditLog:
    def log(self, session_id, tool_name, params, result, success, duration_ms) -> None:
        asyncio.create_task(self._write(session_id, tool_name, params, result, success, duration_ms))

    @staticmethod
    async def _write(session_id, tool_name, params, result, success, duration_ms) -> None:
        try:
            from memory.db import get_db
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO audit_log
                       (id, session_id, tool_name, params, result, success, duration_ms)
                       VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?)""",
                    (session_id, tool_name,
                     json.dumps(params, ensure_ascii=False),
                     str(result)[:2000], 1 if success else 0, duration_ms),
                )
                await db.commit()
        except Exception:
            pass
