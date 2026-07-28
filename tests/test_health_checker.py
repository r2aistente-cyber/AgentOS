"""Tests de HealthChecker._check_all — en particular la recuperación de un
agente marcado 'error' por un falso positivo (ver Piezas de RAG no-bloqueante
y agent_manager.start(): un agente vivo y sano no debía quedar "error" para
siempre sin volver a chequearse — bug real reportado por Xavier)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from hub.health_checker import HealthChecker
from hub.models import AgentInfo


def _fake_manager(status: str, is_alive: bool = True):
    manager = MagicMock()
    info = AgentInfo(name="agente1", port=9000, dir="/tmp/agente1",
                      install_path="/tmp/agente1", status=status, auto_restart=False)
    manager.list.return_value = [info]
    manager.agents = {"agente1": info}

    proc = MagicMock()
    proc.is_alive = is_alive
    proc.pid = 123
    proc.health_url = "http://127.0.0.1:9000/api/v1/health"
    manager.processes = {"agente1": proc}

    def _set_status(name, new_status):
        manager.agents[name].status = new_status
    manager._set_status.side_effect = _set_status

    return manager, proc


@pytest.mark.asyncio
async def test_agente_en_error_que_vuelve_a_responder_se_recupera_a_online():
    manager, proc = _fake_manager(status="error", is_alive=True)
    checker = HealthChecker(manager)

    client = AsyncMock()
    client.get.return_value = httpx.Response(200, request=httpx.Request("GET", proc.health_url))

    await checker._check_all(client)

    assert manager.agents["agente1"].status == "online"
    manager._set_status.assert_called_once_with("agente1", "online")


@pytest.mark.asyncio
async def test_agente_en_error_que_sigue_sin_responder_se_queda_en_error():
    manager, proc = _fake_manager(status="error", is_alive=True)
    checker = HealthChecker(manager)

    client = AsyncMock()
    client.get.side_effect = httpx.ConnectError("no responde")

    await checker._check_all(client)

    # _handle_down no debe re-disparar log/acción para lo que ya estaba en error
    manager._set_status.assert_not_called()
    assert manager.agents["agente1"].status == "error"


@pytest.mark.asyncio
async def test_agente_online_que_deja_de_responder_pasa_a_error():
    manager, proc = _fake_manager(status="online", is_alive=True)
    checker = HealthChecker(manager)

    client = AsyncMock()
    client.get.side_effect = httpx.TimeoutException("timeout")

    await checker._check_all(client)

    manager._set_status.assert_called_once_with("agente1", "error")


@pytest.mark.asyncio
async def test_agente_offline_no_se_chequea():
    manager, proc = _fake_manager(status="offline", is_alive=True)
    checker = HealthChecker(manager)

    client = AsyncMock()
    await checker._check_all(client)

    client.get.assert_not_called()
    manager._set_status.assert_not_called()
