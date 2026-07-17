"""Endpoints de especialidades."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/specialties", tags=["specialties"])

_SPECIALTIES_DIR = Path(__file__).parent.parent.parent / "specialties"


def _load_all() -> list[dict]:
    result = []
    for f in sorted(_SPECIALTIES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append(data)
        except Exception:
            pass
    return result


@router.get("")
async def list_specialties():
    return _load_all()


@router.get("/{specialty_id}")
async def get_specialty(specialty_id: str):
    path = _SPECIALTIES_DIR / f"{specialty_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Especialidad '{specialty_id}' no encontrada")
    return json.loads(path.read_text(encoding="utf-8"))
