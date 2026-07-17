"""
WhatsApp channel — arranca el sidecar Node.js y habla con él via HTTP.
El sidecar corre en localhost:3099 (separado del puerto del sidecar de marketing-agent).
"""
from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

import httpx

from backend.channels.base import Channel

_SIDECAR_DIR = Path(__file__).parent / "whatsapp_sidecar"
_SIDECAR_PORT = 3099
_SIDECAR_URL = f"http://localhost:{_SIDECAR_PORT}"

_proc: subprocess.Popen | None = None


class WhatsAppChannel(Channel):
    async def connect(self) -> None:
        global _proc
        if _proc and _proc.poll() is None:
            return  # ya está corriendo

        if not (_SIDECAR_DIR / "server.js").exists():
            raise RuntimeError("Sidecar no encontrado. Ejecuta: cd channels/whatsapp_sidecar && npm install")

        node = "node"
        _proc = subprocess.Popen(
            [node, "server.js"],
            cwd=_SIDECAR_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        # Esperar a que arranque
        for _ in range(15):
            await asyncio.sleep(1)
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    r = await client.get(f"{_SIDECAR_URL}/status")
                    if r.status_code == 200:
                        return
            except Exception:
                pass
        raise RuntimeError("El sidecar no arrancó en 15 segundos")

    async def send(self, to: str, text: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(f"{_SIDECAR_URL}/send", json={"to": to, "message": text})
            r.raise_for_status()

    async def status(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{_SIDECAR_URL}/status")
                return r.json()
        except Exception:
            return {"connected": False, "sidecar": "offline"}

    async def get_qr(self) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{_SIDECAR_URL}/qr")
                if r.status_code == 200:
                    return r.json().get("qr")
        except Exception:
            pass
        return None

    async def stop(self) -> None:
        global _proc
        if _proc:
            _proc.terminate()
            _proc = None


# Instancia global
whatsapp = WhatsAppChannel()
