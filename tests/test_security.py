"""Tests de seguridad: Sandbox, PermissionEnforcer, ToolOrchestrator.

Migrado desde la v1 (backend.security.*, ya eliminado) al modelo actual
de hub/templates/security/*: permisos por agente (allow/deny en vez de
niveles numéricos globales) y gate de confirmación (`requires_confirm`)
en el orquestador.

La sección de exec_command de la v1 se eliminó: está cubierta con más
profundidad por tests/s8/test_exec_security.py contra el exec_tools.py
actual (la v1 probaba `backend.tools.dev_tools.system_tools`, que ya no
existe, y documentaba con xfail bugs que ya se corrigieron).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _template_support import (  # noqa: E402
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


@pytest.fixture
def template_env(tmp_path):
    """Entorno base (allow=*, deny=[]). Los tests que necesitan otra config
    de tools/security usan install_agent_config() de nuevo dentro de un
    try/finally propio antes de importar el módulo bajo test."""
    cfg = default_config(tmp_path)
    cfg["agent"]["name"] = "security-test-agent"
    install_agent_config(tmp_path, cfg)

    yield tmp_path

    cleanup_template_modules()


@pytest_asyncio.fixture
async def db(template_env):
    import memory.db as db_mod
    db_mod._DB_PATH = template_env / "memory.db"
    from memory.db import init_db
    await init_db()
    yield db_mod._DB_PATH


# ═══════════════════════════════════════════════════════════════
#  SANDBOX
# ═══════════════════════════════════════════════════════════════

def test_sandbox_ruta_relativa_dentro(template_env):
    import security.sandbox as sb_mod

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        result = sb_mod.Sandbox.resolve("archivo.txt")
        assert str(result).startswith(str(template_env))


def test_sandbox_ruta_absoluta_dentro(template_env):
    import security.sandbox as sb_mod
    target = template_env / "sub" / "file.txt"

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        result = sb_mod.Sandbox.resolve(str(target))
        assert result == target.resolve()


def test_sandbox_path_traversal_bloqueado(template_env):
    import security.sandbox as sb_mod

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        with pytest.raises(PermissionError):
            sb_mod.Sandbox.resolve("../../etc/passwd")


def test_sandbox_ruta_absoluta_fuera_bloqueada(template_env):
    import security.sandbox as sb_mod

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        with pytest.raises(PermissionError):
            sb_mod.Sandbox.resolve("/etc/shadow")


def test_sandbox_etc_passwd_bloqueado(template_env):
    import security.sandbox as sb_mod

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        with pytest.raises(PermissionError):
            sb_mod.Sandbox.resolve("/etc/passwd")


def test_sandbox_home_fuera_de_sandbox_bloqueado(template_env):
    import security.sandbox as sb_mod
    home = Path.home()

    with patch.object(sb_mod, "_allowed_dirs", return_value=[template_env]):
        with pytest.raises(PermissionError):
            sb_mod.Sandbox.resolve(str(home / ".bashrc"))


# ═══════════════════════════════════════════════════════════════
#  PERMISSION ENFORCER — modelo por agente (allow/deny), no niveles
# ═══════════════════════════════════════════════════════════════

def test_permission_allow_star_permite_todo(template_env):
    from security.permissions import PermissionEnforcer
    assert PermissionEnforcer().is_allowed("cualquier_tool") is True


def test_permission_deny_bloquea_aunque_este_en_allow_star(tmp_path):
    cfg = default_config(tmp_path)
    cfg["tools"] = {"allow": ["*"], "deny": ["exec_command"]}
    install_agent_config(tmp_path, cfg)
    try:
        from security.permissions import PermissionEnforcer
        assert PermissionEnforcer().is_allowed("exec_command") is False
        assert PermissionEnforcer().is_allowed("read_file") is True
    finally:
        cleanup_template_modules()


def test_permission_allow_list_restringe(tmp_path):
    cfg = default_config(tmp_path)
    cfg["tools"] = {"allow": ["read_file"], "deny": []}
    install_agent_config(tmp_path, cfg)
    try:
        from security.permissions import PermissionEnforcer
        enforcer = PermissionEnforcer()
        assert enforcer.is_allowed("read_file") is True
        assert enforcer.is_allowed("exec_command") is False
    finally:
        cleanup_template_modules()


# ═══════════════════════════════════════════════════════════════
#  TOOL ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

async def test_orchestrator_tool_inexistente(template_env):
    from tools.orchestrator import ToolOrchestrator
    from llm.adapter import ToolCall

    orch = ToolOrchestrator()
    tc = ToolCall(id="t1", name="tool_que_no_existe", arguments={})
    result = await orch.execute(tc)
    assert result.success is False
    assert "no existe" in result.error


async def test_orchestrator_tool_no_permitida(tmp_path):
    cfg = default_config(tmp_path)
    cfg["tools"] = {"allow": ["*"], "deny": ["_test_denied"]}
    install_agent_config(tmp_path, cfg)
    try:
        from tools.orchestrator import ToolOrchestrator
        from tools.registry import register, ToolDef
        from llm.adapter import ToolCall

        register(ToolDef(
            name="_test_denied", description="d", category="test",
            parameters={"type": "object", "properties": {}}, handler=lambda: "x",
        ))
        orch = ToolOrchestrator()
        tc = ToolCall(id="t2", name="_test_denied", arguments={})
        result = await orch.execute(tc)
        assert result.success is False
        assert "no está en la lista" in result.error
    finally:
        cleanup_template_modules()


async def test_orchestrator_tool_exitosa(template_env):
    from tools.orchestrator import ToolOrchestrator
    from tools.registry import register, ToolDef
    from llm.adapter import ToolCall

    register(ToolDef(
        name="_test_echo", description="Echo para tests", category="test",
        parameters={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
        handler=lambda msg: f"echo:{msg}",
    ))

    orch = ToolOrchestrator()
    tc = ToolCall(id="t3", name="_test_echo", arguments={"msg": "hola"})
    result = await orch.execute(tc)
    assert result.success is True
    assert result.raw == "echo:hola"


async def test_orchestrator_registra_en_audit(db):
    from tools.orchestrator import ToolOrchestrator
    from tools.registry import ToolDef, register
    from llm.adapter import ToolCall
    from memory.db import get_db

    register(ToolDef(
        name="_test_audit", description="Audit test", category="test",
        parameters={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
        handler=lambda x: "ok",
    ))

    sid = "test-session-audit"
    orch = ToolOrchestrator(session_id=sid)
    tc = ToolCall(id="t4", name="_test_audit", arguments={"x": "val"})
    await orch.execute(tc)
    await asyncio.sleep(0.05)  # AuditLog usa create_task()

    async with get_db() as db_conn:
        async with db_conn.execute(
            "SELECT * FROM audit_log WHERE tool_name='_test_audit' AND session_id=?", (sid,)
        ) as cur:
            row = await cur.fetchone()
    assert row is not None
    assert row["success"] == 1


async def test_orchestrator_fallo_registra_en_audit(db):
    from tools.orchestrator import ToolOrchestrator
    from tools.registry import register, ToolDef
    from llm.adapter import ToolCall
    from memory.db import get_db

    def _raise(**kwargs):
        raise ValueError("error intencional de test")

    register(ToolDef(
        name="_test_fail_audit", description="Fail audit test", category="test",
        parameters={"type": "object", "properties": {}}, handler=_raise,
    ))

    orch = ToolOrchestrator(session_id="test-fail-sid")
    tc = ToolCall(id="t5", name="_test_fail_audit", arguments={})
    result = await orch.execute(tc)
    await asyncio.sleep(0.05)

    assert result.success is False
    async with get_db() as db_conn:
        async with db_conn.execute(
            "SELECT success FROM audit_log WHERE tool_name='_test_fail_audit'"
        ) as cur:
            row = await cur.fetchone()
    assert row["success"] == 0


async def test_orchestrator_requiere_confirmacion(tmp_path):
    """requires_confirm=True + security.level>=2 → bloquea y guarda pending."""
    cfg = default_config(tmp_path)
    cfg["security"]["level"] = 2
    install_agent_config(tmp_path, cfg)
    try:
        from tools.orchestrator import ToolOrchestrator, get_pending_tool
        from tools.registry import register, ToolDef
        from llm.adapter import ToolCall

        register(ToolDef(
            name="_test_confirm", description="d", category="test",
            parameters={"type": "object", "properties": {}}, handler=lambda: "x",
            requires_confirm=True,
        ))
        orch = ToolOrchestrator(session_id="confirm-sid")
        tc = ToolCall(id="t6", name="_test_confirm", arguments={})
        result = await orch.execute(tc)
        assert result.success is False
        assert result.blocked is True
        assert get_pending_tool("confirm-sid") is not None
    finally:
        cleanup_template_modules()


async def test_orchestrator_confirmacion_permite_ejecutar(tmp_path):
    cfg = default_config(tmp_path)
    cfg["security"]["level"] = 2
    install_agent_config(tmp_path, cfg)
    try:
        from tools.orchestrator import ToolOrchestrator, mark_confirmed
        from tools.registry import register, ToolDef
        from llm.adapter import ToolCall

        register(ToolDef(
            name="_test_confirm2", description="d", category="test",
            parameters={"type": "object", "properties": {}}, handler=lambda: "hecho",
            requires_confirm=True,
        ))
        sid = "confirm-sid-2"
        orch = ToolOrchestrator(session_id=sid)
        tc = ToolCall(id="t7", name="_test_confirm2", arguments={})
        await orch.execute(tc)  # queda pendiente

        confirmed_tc = mark_confirmed(sid)
        assert confirmed_tc is not None
        result = await orch.execute(confirmed_tc)
        assert result.success is True
        assert result.raw == "hecho"
    finally:
        cleanup_template_modules()
