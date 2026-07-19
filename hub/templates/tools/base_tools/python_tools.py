"""Tool run_python — ejecuta un script Python en un archivo temporal del sandbox."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

import agent_config as config
from tools.registry import ToolDef, register


async def run_python(script: str, timeout: int = 120) -> str:
    """Escribe el script en un archivo temporal dentro del sandbox y lo ejecuta."""
    timeout = min(timeout, 300)

    sandbox_paths: list[str] = (config.get("security.sandbox_paths") or [])
    sandbox = Path(sandbox_paths[0]) if sandbox_paths else Path(config.get("agent.install_path", ".")) / "data"
    sandbox.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", dir=sandbox, delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp_path = Path(f.name)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(tmp_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(sandbox),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace").strip()
        return output[:8000] if output else f"(sin salida, código {proc.returncode})"
    except asyncio.TimeoutError:
        return f"[TIMEOUT] El script tardó más de {timeout}s y fue cancelado."
    except Exception as e:
        return f"[ERROR] {e}"
    finally:
        tmp_path.unlink(missing_ok=True)


register(ToolDef(
    name="run_python",
    description=(
        "Ejecuta un script Python y devuelve su salida. "
        "Úsalo cuando necesites cálculos, manipulación de datos, instalar paquetes "
        "o cualquier lógica que requiera Python. El script corre en el sandbox del agente."
    ),
    category="system",
    dangerous=False,
    requires_confirm=False,
    parameters={
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "Código Python completo a ejecutar",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout en segundos (default 120, máx 300)",
                "default": 120,
            },
        },
        "required": ["script"],
    },
    handler=run_python,
))
