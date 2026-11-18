"""Busqueda en los manuales oficiales de DaVinci Resolve (indice local con cita de pagina).

El indice y el codigo de busqueda viven aparte (carpeta `manuales_resolve.dir` del config,
por defecto ~/resolve-agente) porque necesitan torch/sentence-transformers: aqui solo se
invoca su CLI con el python de ese entorno y se lee el JSON.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import agent_config as config
from tools.registry import ToolDef, register

_TIMEOUT_S = 120  # la primera consulta carga el modelo de embeddings


def _dir_manuales() -> Path:
    cfg = (config.get("manuales_resolve", {}) or {}).get("dir")
    return Path(cfg).expanduser() if cfg else Path.home() / "resolve-agente"


def _python_de(base: Path) -> Path:
    rel = ".venv/Scripts/python.exe" if sys.platform == "win32" else ".venv/bin/python"
    return base / rel


async def buscar_manual_resolve(consulta: str, consulta_en: str = "", k: int = 5) -> str:
    base = _dir_manuales()
    py, script = _python_de(base), base / "buscar.py"
    if not py.exists() or not script.exists() or not (base / "indice" / "indice.db").exists():
        raise RuntimeError(f"Indice de manuales no disponible en {base}")

    args = [str(py), "-W", "ignore", str(script), consulta, "-k", str(max(1, min(int(k), 8))), "--json"]
    if consulta_en.strip():
        args += ["--en", consulta_en.strip()]
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=str(base), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("La busqueda en los manuales supero el tiempo limite")
    if proc.returncode != 0:
        raise RuntimeError(f"Fallo la busqueda en los manuales: {err.decode(errors='replace')[-300:]}")
    data = json.loads(out.decode("utf-8").strip().splitlines()[-1])

    if not data["encontrado"]:
        return (f"NO ENCONTRADO (mejor similitud {data['mejor_similitud']:.2f}, bajo el umbral). "
                "Dile al usuario que no lo encuentras en los manuales; no respondas de memoria.")
    partes = [f"Similitud maxima {data['mejor_similitud']:.2f}. Fragmentos de los manuales oficiales "
              "(cita documento y pagina; si ninguno responde la pregunta, di que no lo encuentras):"]
    for r in data["resultados"]:
        texto = r["texto"].strip()
        partes.append(f"\n[{r['doc']}, p.{r['pagina']}]\n{texto}")
    return "\n".join(partes)


register(ToolDef(
    "buscar_manual_resolve",
    "Busca en los manuales oficiales de DaVinci Resolve (manual de referencia 21, guias del editor, "
    "Fairlight y principiantes de la 20). Devuelve fragmentos con documento y pagina. Usala SIEMPRE antes "
    "de responder una pregunta sobre Resolve. Pasa la pregunta en espanol en `consulta` y, ademas, la misma "
    "idea con los nombres de menus, paneles y herramientas en ingles en `consulta_en` (los manuales estan en ingles).",
    "knowledge",
    {"type": "object", "properties": {
        "consulta": {"type": "string", "description": "La pregunta del usuario en espanol"},
        "consulta_en": {"type": "string", "description": "Terminos equivalentes en ingles, ej. 'noise reduction voice isolation Fairlight'"},
        "k": {"type": "integer", "default": 5, "description": "Cuantos fragmentos (1-8)"}},
     "required": ["consulta"]},
    buscar_manual_resolve))
