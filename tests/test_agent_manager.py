"""Tests de AgentManager: creación y sincronización de código desde template.

Aislamiento: hub.config.templates_dir/agents_dir/registry_path/port_range
apuntan a tmp_path — nunca se toca ~/AgentOS real.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def manager_env(tmp_path):
    """Template mínimo + agents_dir/registry_path/port_range en tmp_path."""
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "default_config.yaml").write_text(
        "llm:\n  provider: mock\n  model: test\n", encoding="utf-8"
    )
    (templates / "engine.py").write_text("VERSION = 1\n", encoding="utf-8")
    tools_dir = templates / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")

    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    registry_path = tmp_path / "agents.json"

    import hub.config as cfg
    with patch.object(cfg, "templates_dir", return_value=templates), \
         patch.object(cfg, "agents_dir", return_value=agents_dir), \
         patch.object(cfg, "registry_path", return_value=registry_path), \
         patch.object(cfg, "port_range", return_value=(9000, 9010)):
        yield {"templates": templates, "agents_dir": agents_dir}


def test_create_copia_el_template(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    info = mgr.create("agente1", {})
    agent_dir = Path(info.dir)

    assert (agent_dir / "engine.py").read_text(encoding="utf-8") == "VERSION = 1\n"
    assert (agent_dir / "tools" / "__init__.py").exists()
    assert (agent_dir / "config.yaml").exists()


def test_sync_from_template_actualiza_codigo_sin_tocar_config_ni_data(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    info = mgr.create("agente2", {})
    agent_dir = Path(info.dir)

    # El usuario "customizó" su config y tiene datos propios en el workspace.
    (agent_dir / "config.yaml").write_text("custom: true\n", encoding="utf-8")
    (agent_dir / "data").mkdir(exist_ok=True)
    (agent_dir / "data" / "mio.txt").write_text("no tocar", encoding="utf-8")

    # El template se actualiza (simula un fix como los de esta sesión).
    (manager_env["templates"] / "engine.py").write_text("VERSION = 2\n", encoding="utf-8")

    mgr.sync_from_template("agente2")

    assert (agent_dir / "engine.py").read_text(encoding="utf-8") == "VERSION = 2\n"
    assert (agent_dir / "config.yaml").read_text(encoding="utf-8") == "custom: true\n"
    assert (agent_dir / "data" / "mio.txt").read_text(encoding="utf-8") == "no tocar"


def test_sync_from_template_agente_inexistente_da_keyerror(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    with pytest.raises(KeyError):
        mgr.sync_from_template("no_existe")


def test_sync_from_template_agrega_archivos_nuevos_del_template(manager_env):
    """Si el template ganó un archivo/paquete nuevo desde que se creó el
    agente, sync también lo copia (no solo actualiza los que ya existían)."""
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    mgr.create("agente3", {})

    (manager_env["templates"] / "rag").mkdir()
    (manager_env["templates"] / "rag" / "__init__.py").write_text("", encoding="utf-8")

    info = mgr.sync_from_template("agente3")
    assert (Path(info.dir) / "rag" / "__init__.py").exists()


def test_start_no_relanza_si_ya_responde_en_su_puerto(manager_env):
    """Reproduce el bug real: el Hub se reinicia y pierde en memoria el
    handle del subproceso de un agente que sigue vivo de una vida anterior
    (`self.processes` se vacía) — un `AgentProcess` recién creado siempre
    empieza con `is_alive=False`. Sin chequear el puerto primero, `start()`
    lanzaba un segundo uvicorn que chocaba de puerto contra el que ya
    estaba sirviendo (visto varias veces en la sesión real)."""
    from unittest.mock import MagicMock, patch
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    mgr.create("agente4", {})
    mgr._set_status("agente4", "error")  # simula el falso positivo del healthchecker

    # El Hub "se reinició": el AgentProcess trackeado es nuevo, is_alive=False,
    # pero httpx.get al health_url sí responde (proceso real de otra vida).
    with patch.object(AgentManager, "_responde_en_su_puerto", return_value=True):
        info = mgr.start("agente4")

    assert info.status == "online"
    # No se intentó lanzar un subproceso nuevo — is_alive de un AgentProcess
    # recién creado sigue False, así que si start() hubiera llamado a
    # proc.start() habría reventado (no hay agent_main real en el template
    # mínimo de test) en vez de retornar limpio.
    assert mgr.processes["agente4"].is_alive is False


def test_start_lanza_proceso_si_nada_responde_en_el_puerto(manager_env):
    """Caso normal: si el puerto no responde de verdad (nada corriendo
    todavía), start() sí debe intentar lanzar el subproceso."""
    from unittest.mock import MagicMock, patch
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    mgr.create("agente5", {})

    with patch.object(AgentManager, "_responde_en_su_puerto", return_value=False):
        mock_proc = MagicMock()
        mock_proc.is_alive = False
        mock_proc.pid = 12345
        mgr.processes["agente5"] = mock_proc

        mgr.start("agente5")

    mock_proc.start.assert_called_once()
    assert mgr.agents["agente5"].status == "online"


# ─── reserve_port / release_port (hardening del import de agentes) ────────
# Antes, el endpoint de import llamaba _next_port() fuera del lock del
# manager -- dos imports concurrentes podían recibir el mismo puerto.
# reserve_port() lo reserva atómicamente hasta que el caller registra el
# agente o libera la reserva si la operación falla.

def test_reserve_port_no_repite_hasta_liberar(manager_env):
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    p1 = mgr.reserve_port()
    p2 = mgr.reserve_port()
    assert p1 != p2

    mgr.release_port(p1)
    p3 = mgr.reserve_port()
    assert p3 == p1  # vuelve a estar disponible como el primero libre


def test_next_port_salta_uno_ocupado_de_verdad_por_el_so(manager_env):
    """No solo mira el registro en memoria -- hace un bind real. Sin esto,
    un puerto del rango ya usado por otro proceso de la máquina (ej. algo
    del propio despacho) se entregaba igual, y el agente fallaba recién al
    intentar arrancar."""
    import socket
    from hub.agent_manager import AgentManager

    mgr = AgentManager()
    start, _ = (9000, 9010)  # ver port_range parcheado en manager_env
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", start))
    try:
        port = mgr.reserve_port()
        assert port != start
    finally:
        s.close()
