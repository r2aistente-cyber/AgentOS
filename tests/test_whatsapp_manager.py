"""Tests de WhatsAppManager y SidecarProcess (hub/whatsapp_manager.py).

Aislamiento:
- subprocess.Popen mockeado — nunca se lanza Node.js real
- httpx.get mockeado — nunca se contacta al sidecar real
- hub.config.templates_dir() apunta a un directorio temporal
"""
from __future__ import annotations

import signal
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _mock_proc(alive: bool = True, pid: int = 12345) -> MagicMock:
    """Crea un mock de subprocess.Popen."""
    proc = MagicMock()
    proc.pid = pid
    # poll() retorna None si el proceso sigue vivo
    proc.poll = MagicMock(return_value=None if alive else 0)
    proc.wait = MagicMock()
    proc.send_signal = MagicMock()
    proc.kill = MagicMock()
    return proc


@pytest.fixture(autouse=True)
def _patch_config(tmp_path):
    """Redirige templates_dir() a tmp_path para evitar rutas reales."""
    import hub.config as cfg
    with patch.object(cfg, "templates_dir", return_value=tmp_path):
        yield


# ─── SidecarProcess.is_alive ──────────────────────────────────────────────────

def test_sidecar_is_alive_sin_proceso():
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("test", 3100, 8000, Path("/tmp/sess"), [])
    assert sc.is_alive is False


def test_sidecar_is_alive_proceso_vivo(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("test", 3100, 8000, tmp_path / "sess", [])
    sc._proc = _mock_proc(alive=True)
    assert sc.is_alive is True


def test_sidecar_is_alive_proceso_muerto(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("test", 3100, 8000, tmp_path / "sess", [])
    sc._proc = _mock_proc(alive=False)
    assert sc.is_alive is False


# ─── SidecarProcess.start ─────────────────────────────────────────────────────

def test_sidecar_start_lanza_proceso(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("mi-agente", 3101, 8001, tmp_path / "sess", ["123456"])

    mock_proc = _mock_proc()
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        sc.start()

    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    cmd = args[0]
    assert cmd[0] == "node"
    assert sc._proc is mock_proc


def test_sidecar_start_crea_session_dir(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sess = tmp_path / "sess" / "deep"
    sc = SidecarProcess("ag", 3102, 8002, sess, [])

    with patch("subprocess.Popen", return_value=_mock_proc()):
        sc.start()

    assert sess.exists()


def test_sidecar_start_idempotente(tmp_path):
    """Si ya está vivo, start() no lanza otro proceso."""
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("ag", 3103, 8003, tmp_path / "sess", [])
    sc._proc = _mock_proc(alive=True)

    with patch("subprocess.Popen") as mock_popen:
        sc.start()

    mock_popen.assert_not_called()


def test_sidecar_start_env_vars(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("mi-ag", 3110, 8010, tmp_path / "sess", ["111", "222"])

    captured_env = {}
    original_popen = subprocess.Popen

    def fake_popen(cmd, *, env, **kw):
        captured_env.update(env)
        return _mock_proc()

    with patch("subprocess.Popen", side_effect=fake_popen):
        sc.start()

    assert captured_env["WA_SIDECAR_PORT"] == "3110"
    assert captured_env["WA_AGENT_PORT"] == "8010"
    assert captured_env["WA_AGENT_NAME"] == "mi-ag"
    assert "111" in captured_env["WA_ALLOWED_NUMBERS"]


# ─── SidecarProcess.stop ─────────────────────────────────────────────────────

def test_sidecar_stop_sin_proceso_no_falla():
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("ag", 3104, 8004, Path("/tmp"), [])
    sc.stop()  # no debe lanzar excepción
    assert sc._proc is None


def test_sidecar_stop_mata_proceso(tmp_path):
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("ag", 3105, 8005, tmp_path / "s", [])
    mock_proc = _mock_proc()
    sc._proc = mock_proc

    import sys
    if sys.platform != "win32":
        sc.stop()
        mock_proc.send_signal.assert_called_once_with(signal.SIGTERM)
    else:
        sc.stop()

    assert sc._proc is None


# ─── WhatsAppManager._next_port ───────────────────────────────────────────────

def test_next_port_inicial_es_3100():
    from hub.whatsapp_manager import WhatsAppManager, _SIDECAR_BASE_PORT
    mgr = WhatsAppManager()
    assert mgr._next_port() == _SIDECAR_BASE_PORT


def test_next_port_incrementa_si_ocupado():
    from hub.whatsapp_manager import WhatsAppManager, _SIDECAR_BASE_PORT
    mgr = WhatsAppManager()
    p1 = mgr._next_port()
    p2 = mgr._next_port()
    p3 = mgr._next_port()
    assert p2 == p1 + 1
    assert p3 == p1 + 2


def test_next_port_reutiliza_liberados():
    from hub.whatsapp_manager import WhatsAppManager, _SIDECAR_BASE_PORT
    mgr = WhatsAppManager()
    p1 = mgr._next_port()
    mgr._ports_used.discard(p1)
    p2 = mgr._next_port()
    assert p2 == p1


# ─── WhatsAppManager.start ────────────────────────────────────────────────────

def test_manager_start_crea_sidecar(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()):
        sc = mgr.start("agente1", 8001, tmp_path / "sess")

    assert "agente1" in mgr._sidecars
    assert sc.is_alive is True


def test_manager_start_idempotente(tmp_path):
    """Llamar start() dos veces para el mismo agente retorna el mismo sidecar."""
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()) as mock_popen:
        sc1 = mgr.start("ag", 8002, tmp_path / "s1")
        sc2 = mgr.start("ag", 8002, tmp_path / "s1")

    assert sc1 is sc2
    mock_popen.assert_called_once()  # Popen solo se llama una vez


def test_manager_start_puertos_distintos_por_agente(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()):
        sc1 = mgr.start("ag1", 8001, tmp_path / "s1")
        sc2 = mgr.start("ag2", 8002, tmp_path / "s2")

    assert sc1.sidecar_port != sc2.sidecar_port


# ─── WhatsAppManager.stop ─────────────────────────────────────────────────────

def test_manager_stop_elimina_sidecar(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()):
        mgr.start("ag", 8003, tmp_path / "s")

    assert "ag" in mgr._sidecars
    mgr.stop("ag")
    assert "ag" not in mgr._sidecars


def test_manager_stop_libera_puerto(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager, _SIDECAR_BASE_PORT
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()):
        mgr.start("ag", 8004, tmp_path / "s")

    port = mgr._sidecars["ag"].sidecar_port if "ag" in mgr._sidecars else _SIDECAR_BASE_PORT
    mgr.stop("ag")
    assert port not in mgr._ports_used


def test_manager_stop_agente_inexistente_no_falla():
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr.stop("no_existe")  # no debe lanzar excepción


# ─── WhatsAppManager.stop_all ─────────────────────────────────────────────────

def test_manager_stop_all(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()

    with patch("subprocess.Popen", return_value=_mock_proc()):
        mgr.start("ag1", 8001, tmp_path / "s1")
        mgr.start("ag2", 8002, tmp_path / "s2")

    mgr.stop_all()
    assert len(mgr._sidecars) == 0


# ─── WhatsAppManager.status ───────────────────────────────────────────────────

def test_manager_status_sin_sidecar():
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    s = mgr.status("no_existe")
    assert s["running"] is False
    assert s["ready"] is False


def test_manager_status_sidecar_muerto(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_dead_sidecar(tmp_path)
    s = mgr.status("ag")
    assert s["running"] is False


def test_manager_status_sidecar_vivo_responde(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_alive_sidecar(tmp_path, 3150)

    mock_r = MagicMock()
    mock_r.json.return_value = {"ready": True, "waiting_qr": False}

    with patch("httpx.get", return_value=mock_r):
        s = mgr.status("ag")

    assert s["running"] is True
    assert s["ready"] is True
    assert s["sidecar_port"] == 3150


def test_manager_status_sidecar_vivo_sin_respuesta(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_alive_sidecar(tmp_path, 3151)

    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        s = mgr.status("ag")

    assert s["running"] is True
    assert s["ready"] is False
    assert "error" in s


# ─── WhatsAppManager.get_qr ───────────────────────────────────────────────────

def test_manager_get_qr_sin_sidecar():
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    assert mgr.get_qr("no_existe") is None


def test_manager_get_qr_sidecar_muerto(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_dead_sidecar(tmp_path)
    assert mgr.get_qr("ag") is None


def test_manager_get_qr_retorna_datos(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_alive_sidecar(tmp_path, 3160)

    mock_r = MagicMock()
    mock_r.status_code = 200
    mock_r.json.return_value = {"qr": "data:image/png;base64,ABC"}

    with patch("httpx.get", return_value=mock_r):
        qr = mgr.get_qr("ag")

    assert qr is not None
    assert "qr" in qr


def test_manager_get_qr_error_retorna_none(tmp_path):
    from hub.whatsapp_manager import WhatsAppManager
    mgr = WhatsAppManager()
    mgr._sidecars["ag"] = _make_alive_sidecar(tmp_path, 3161)

    with patch("httpx.get", side_effect=Exception("network error")):
        qr = mgr.get_qr("ag")

    assert qr is None


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _make_dead_sidecar(tmp_path: Path) -> "SidecarProcess":
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("ag", 3199, 8099, tmp_path / "s", [])
    sc._proc = _mock_proc(alive=False)
    return sc


def _make_alive_sidecar(tmp_path: Path, port: int) -> "SidecarProcess":
    from hub.whatsapp_manager import SidecarProcess
    sc = SidecarProcess("ag", port, 8099, tmp_path / "s", [])
    sc._proc = _mock_proc(alive=True)
    return sc
