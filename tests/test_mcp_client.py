"""Tests de tools/mcp_client.py contra un servidor MCP real (FastMCP, en
un thread con uvicorn en un puerto libre) — MCP tiene suficientes detalles
de protocolo (handshake, sesión, streaming) que mockear a bajo nivel
arriesga probar una implementación de juguete en vez del comportamiento
real; un servidor real, aunque más lento, es la fuente de verdad.

Nota importante: discover_and_register() usa anyio.run() internamente —
en producción esto es seguro porque se llama al importar el paquete de
tools, ANTES de que uvicorn arranque su propio event loop. En los tests
hay que respetar la misma condición: llamarlo desde un fixture/función
síncrona, nunca desde dentro de un test `async def` (ya tiene su propio
loop corriendo vía pytest-asyncio, y anyio.run() no puede anidarse).
"""
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _template_support import (  # noqa: E402
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def mcp_test_server():
    """Servidor MCP real con 2 tools: una normal y una que siempre falla."""
    port = _puerto_libre()
    server = FastMCP("test-server", stateless_http=True)

    @server.tool()
    async def sumar(a: int, b: int) -> str:
        """Suma dos numeros."""
        return str(a + b)

    @server.tool()
    async def tool_que_falla() -> str:
        """Siempre lanza una excepción."""
        raise RuntimeError("fallo intencional de la tool")

    app = server.streamable_http_app()
    config_uv = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server_uv = uvicorn.Server(config_uv)

    thread = threading.Thread(target=server_uv.run, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while not server_uv.started and time.time() < deadline:
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}/mcp"

    server_uv.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def tools_descubiertas(tmp_path, mcp_test_server):
    """Instala el config con el servidor MCP de prueba y corre
    discover_and_register() de forma síncrona (fixture, sin event loop
    activo todavía) — igual que pasa en producción al importar el paquete
    de tools. Retorna cuántas tools se registraron."""
    cfg = default_config(tmp_path)
    cfg["mcp_servers"] = [{"name": "suite_legal", "url": mcp_test_server, "api_key": "clave-test"}]
    install_agent_config(tmp_path, cfg)

    from tools import mcp_client
    n = mcp_client.discover_and_register()

    yield n

    cleanup_template_modules()


def test_discover_and_register_encuentra_las_tools(tools_descubiertas):
    from tools import registry

    assert tools_descubiertas == 2
    assert registry.get("sumar") is not None
    assert registry.get("tool_que_falla") is not None


@pytest.mark.asyncio
async def test_tool_descubierta_ejecuta_de_verdad(tools_descubiertas):
    from tools import registry

    tool = registry.get("sumar")
    resultado = await tool.handler(a=3, b=4)

    assert resultado == "7"


def test_schema_de_la_tool_descubierta_viene_del_servidor(tools_descubiertas):
    from tools import registry

    tool = registry.get("sumar")

    assert tool.parameters["required"] == ["a", "b"]
    assert tool.parameters["properties"]["a"]["type"] == "integer"


@pytest.mark.asyncio
async def test_fallo_de_la_tool_remota_no_crashea_el_handler(tools_descubiertas):
    """Si la tool del lado del servidor lanza una excepción, el handler
    genérico del cliente debe devolver un string de error legible, no
    propagar la excepción (mismo criterio que el resto del motor: un
    fallo de tool no debe tumbar la conversación)."""
    from tools import registry

    tool = registry.get("tool_que_falla")
    resultado = await tool.handler()

    assert "error" in resultado.lower()


def test_servidor_inexistente_no_rompe_el_arranque(tmp_path):
    """Si el servidor MCP configurado no responde (url incorrecta, caído),
    discover_and_register() no debe lanzar — el agente sigue arrancando
    sin esas tools."""
    cfg = default_config(tmp_path)
    cfg["mcp_servers"] = [{"name": "caido", "url": "http://127.0.0.1:1/mcp", "api_key": "x"}]
    install_agent_config(tmp_path, cfg)

    try:
        from tools import mcp_client
        n = mcp_client.discover_and_register()
        assert n == 0
    finally:
        cleanup_template_modules()


def test_sin_mcp_servers_configurados_no_hace_nada(tmp_path):
    cfg = default_config(tmp_path)
    install_agent_config(tmp_path, cfg)

    try:
        from tools import mcp_client
        n = mcp_client.discover_and_register()
        assert n == 0
    finally:
        cleanup_template_modules()
