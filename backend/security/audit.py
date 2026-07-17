"""Log de auditoría — solo append, nunca borra."""
from __future__ import annotations

import asyncio
from typing import Any


class AuditLog:
    def log(
        self,
        user_id: str,
        session_id: str | None,
        tool_name: str,
        params: dict,
        result: Any,
        success: bool,
        duration_ms: int,
    ) -> None:
        asyncio.create_task(self._write(user_id, session_id, tool_name, params, result, success, duration_ms))

    @staticmethod
    async def _write(user_id, session_id, tool_name, params, result, success, duration_ms):
        try:
            from backend.memory.db import get_db
            import json
            async with get_db() as db:
                await db.execute(
                    """INSERT INTO audit_log
                       (id, user_id, session_id, tool_name, params, result, success, duration_ms)
                       VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        session_id,
                        tool_name,
                        json.dumps(params, ensure_ascii=False),
                        str(result)[:2000],
                        1 if success else 0,
                        duration_ms,
                    ),
                )
                await db.commit()
        except Exception:
            pass  # auditoría nunca rompe el flujo principal
