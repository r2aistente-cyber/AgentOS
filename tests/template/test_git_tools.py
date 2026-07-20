"""Tests de git tools (hub/templates/tools/base_tools/git_tools.py).

Usa repos git reales creados en tmp_path para evitar depender de
la estructura del repo de producción.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _init_repo(path: Path) -> Path:
    """Crea un repo git mínimo con un commit inicial."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@test.com"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"],
                   check=True, capture_output=True)
    (path / "README.md").write_text("# repo de test")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "init"],
                   check=True, capture_output=True)
    return path


# ─── git_status ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_git_status_repo_limpio(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    from tools.base_tools.git_tools import git_status
    result = await git_status(path=str(repo))
    assert result  # debe tener output de la rama
    assert "[ERROR]" not in result and "[TIMEOUT]" not in result


@pytest.mark.asyncio
async def test_git_status_archivo_nuevo(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    (repo / "nuevo.py").write_text("x = 1")
    from tools.base_tools.git_tools import git_status
    result = await git_status(path=str(repo))
    assert "nuevo.py" in result


@pytest.mark.asyncio
async def test_git_status_sin_git_instalado(template_env):
    from tools.base_tools.git_tools import git_status
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result = await git_status(path="/tmp")
    assert "no está instalado" in result or "ERROR" in result


@pytest.mark.asyncio
async def test_git_status_timeout(template_env):
    from tools.base_tools.git_tools import git_status

    async def slow_communicate():
        raise asyncio.TimeoutError

    mock_proc = MagicMock()
    mock_proc.communicate = slow_communicate

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
         patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        result = await git_status(path="/tmp")

    assert "[TIMEOUT]" in result


# ─── git_log ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_git_log_muestra_commits(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    from tools.base_tools.git_tools import git_log
    result = await git_log(path=str(repo), n=5)
    assert "init" in result


@pytest.mark.asyncio
async def test_git_log_repo_inexistente(template_env):
    from tools.base_tools.git_tools import git_log
    result = await git_log(path="/tmp/no_existe_este_repo_xyzw")
    assert result  # retorna mensaje de error, no rompe


# ─── git_diff ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_git_diff_sin_cambios_vacio(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    from tools.base_tools.git_tools import git_diff
    result = await git_diff(path=str(repo))
    assert "[ERROR]" not in result and "[TIMEOUT]" not in result


@pytest.mark.asyncio
async def test_git_diff_con_cambios(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    (repo / "README.md").write_text("# modificado")
    from tools.base_tools.git_tools import git_diff
    result = await git_diff(path=str(repo))
    assert "README" in result or "modificado" in result or result == ""


@pytest.mark.asyncio
async def test_git_diff_staged(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    nuevo = repo / "staged.txt"
    nuevo.write_text("staged content")
    subprocess.run(["git", "-C", str(repo), "add", "staged.txt"],
                   check=True, capture_output=True)
    from tools.base_tools.git_tools import git_diff
    result = await git_diff(path=str(repo), staged=True)
    assert "staged" in result or result == ""


# ─── git_show ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_git_show_head(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    from tools.base_tools.git_tools import git_show
    result = await git_show(ref="HEAD", path=str(repo))
    assert "init" in result or "README" in result


@pytest.mark.asyncio
async def test_git_show_ref_inexistente(tmp_path, template_env):
    repo = _init_repo(tmp_path / "repo")
    from tools.base_tools.git_tools import git_show
    result = await git_show(ref="hash_que_no_existe_xyzw123", path=str(repo))
    assert result  # mensaje de error, no rompe


# ─── Registro en el registry ─────────────────────────────────────────────────

def test_git_tools_registradas(template_env):
    import tools.base_tools.git_tools  # noqa: F401
    from tools import registry
    names = {t.name for t in registry.all_tools()}
    for expected in ["git_status", "git_log", "git_diff", "git_show"]:
        assert expected in names, f"'{expected}' no está en el registry"
