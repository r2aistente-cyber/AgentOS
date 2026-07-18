"""Navegador de directorios para el selector de ubicación del wizard.

Solo lista carpetas (no archivos) y expone las unidades en Windows. Es de solo
lectura; no crea ni borra nada. El endurecimiento (limitar a rutas permitidas)
es parte del Sprint 8 de seguridad.
"""
from __future__ import annotations

import os
import string
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/hub", tags=["fs"])


def _drives() -> list[str]:
    if os.name == "nt":
        return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    return ["/"]


@router.get("/fs")
def list_dir(path: str | None = None) -> dict:
    """Lista subdirectorios de `path`. Sin `path`, devuelve unidades + home."""
    home = str(Path.home())
    if not path:
        return {"path": "", "parent": None, "drives": _drives(), "dirs": [], "home": home}

    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail="El directorio no existe")

    try:
        dirs = sorted(
            (e.name for e in os.scandir(p) if e.is_dir() and not e.name.startswith(".")),
            key=str.lower,
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Sin permiso para leer ese directorio")

    parent = str(p.parent) if p.parent != p else None
    return {
        "path": str(p),
        "parent": parent,
        "drives": _drives(),
        "dirs": dirs,
        "home": home,
    }
