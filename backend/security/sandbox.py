"""Restringe acceso del agente a carpetas permitidas."""
from __future__ import annotations

from pathlib import Path

import backend.config as config


def _allowed_dirs() -> list[Path]:
    raw = config.get("security.sandbox_paths", [])
    return [Path(p).expanduser().resolve() for p in raw]


class Sandbox:
    @staticmethod
    def resolve(rel_path: str) -> Path:
        """
        Resuelve una ruta relativa dentro del sandbox.
        Lanza PermissionError si intenta salir.
        """
        target = Path(rel_path).expanduser()

        # Ruta absoluta: verificar que está dentro de un dir permitido
        if target.is_absolute():
            resolved = target.resolve()
            for base in _allowed_dirs():
                try:
                    resolved.relative_to(base)
                    return resolved
                except ValueError:
                    continue
            raise PermissionError(f"Ruta fuera del sandbox: {rel_path}")

        # Ruta relativa: buscar en los dirs permitidos
        for base in _allowed_dirs():
            candidate = (base / rel_path).resolve()
            try:
                candidate.relative_to(base)
                return candidate
            except ValueError:
                continue

        # Fallback: primera dir permitida
        dirs = _allowed_dirs()
        if dirs:
            candidate = (dirs[0] / rel_path).resolve()
            try:
                candidate.relative_to(dirs[0])
                return candidate
            except ValueError:
                pass

        raise PermissionError(f"No se puede resolver la ruta: {rel_path}")
