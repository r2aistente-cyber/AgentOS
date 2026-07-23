"""Restringe el acceso a archivos a las carpetas permitidas del agente."""
from __future__ import annotations

from pathlib import Path

import agent_config as config


def _allowed_dirs() -> list[Path]:
    raw = config.get("security.sandbox_paths", []) or []
    dirs = [Path(p).expanduser().resolve() for p in raw]
    if not dirs:
        # Fallback: el data/ del propio agente
        dirs = [(config.AGENT_DIR / "data").resolve()]
    return dirs


class Sandbox:
    @staticmethod
    def primary_dir() -> Path:
        """Devuelve la carpeta principal del workspace del agente."""
        return _allowed_dirs()[0]

    @staticmethod
    def resolve(rel_path: str) -> Path:
        """Resuelve una ruta dentro del sandbox; PermissionError si escapa."""
        target = Path(rel_path).expanduser()
        dirs = _allowed_dirs()

        if target.is_absolute():
            resolved = target.resolve()
            for base in dirs:
                try:
                    resolved.relative_to(base)
                    return resolved
                except ValueError:
                    continue
            raise PermissionError(f"Ruta fuera del sandbox: {rel_path}")

        for base in dirs:
            candidate = (base / rel_path).resolve()
            try:
                candidate.relative_to(base)
                return candidate
            except ValueError:
                continue

        candidate = (dirs[0] / rel_path).resolve()
        try:
            candidate.relative_to(dirs[0])
            return candidate
        except ValueError:
            raise PermissionError(f"No se puede resolver la ruta: {rel_path}")
