"""Cliente MCP genérico — descubre y registra dinámicamente las tools que
exponen los servidores MCP configurados en `config.mcp_servers`, sin
necesitar un archivo de tools escrito a mano por cada integración (ver
Pieza de integración R2 Legal ↔ Suite Legal: antes esto era
`tools/base_tools/suite_legal_tools.py`, con el catálogo de endpoints
copiado a mano en specialties/r2-legal.json — se desactualizó una vez).

Con esto, "acoplar" un agente a CUALQUIER programa que hable MCP es solo
configuración (`mcp_servers: [{name, url, api_key}]`), no código nuevo.

Config esperada en config.yaml:

    mcp_servers:
      - name: suite_legal
        url: http://localhost:8000/mcp
        api_key: <token de la cuenta de servicio>

`discover_and_register()` se llama una vez al importar el paquete de tools
(módulo `tools.base_tools`, antes de que uvicorn arranque su propio event
loop — por eso usa `anyio.run()`, bloqueante, en vez de necesitar await).
Si un servidor no responde, se loguea y se sigue sin esas tools (mismo
criterio de degradación que el resto del motor — un servidor caído no
debe impedir que el agente arranque).
"""
from __future__ import annotations

import logging
from typing import Any

import agent_config as config
from tools.registry import ToolDef, register

log = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 5  # segundos — no dejar que un servidor MCP caído cuelgue el arranque


def _http_client(api_key: str | None, timeout: float):
    import httpx

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    return httpx.AsyncClient(headers=headers, timeout=timeout)


def _make_handler(server_name: str, url: str, api_key: str | None, tool_name: str):
    async def handler(**kwargs: Any) -> str:
        import mcp as mcp_pkg
        from mcp.client.streamable_http import streamable_http_client

        try:
            async with _http_client(api_key, timeout=30) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read, write, _):
                    async with mcp_pkg.ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, kwargs)
        except Exception as e:  # noqa: BLE001
            return f"Error llamando a '{tool_name}' en el servidor MCP '{server_name}': {e}"

        texts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
        out = "\n".join(texts) if texts else (str(result.content) if result.content else "")
        if result.isError:
            return f"Error en '{tool_name}' ({server_name}): {out}"
        return out

    handler.__name__ = f"mcp_{server_name}_{tool_name}"
    return handler


async def _list_tools(url: str, api_key: str | None) -> list:
    import mcp as mcp_pkg
    from mcp.client.streamable_http import streamable_http_client

    async with _http_client(api_key, timeout=_CONNECT_TIMEOUT) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (read, write, _):
            async with mcp_pkg.ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools


def discover_and_register() -> int:
    """Descubre tools de cada servidor en config.mcp_servers y las registra.
    Retorna cuántas tools nuevas se registraron en total."""
    servers = config.get("mcp_servers", []) or []
    if not servers:
        return 0

    import anyio

    multi = len(servers) > 1
    total = 0
    for server in servers:
        name = server.get("name") or "mcp"
        url = server.get("url")
        api_key = server.get("api_key")
        if not url:
            log.warning("Servidor MCP '%s' sin 'url' en config — se ignora", name)
            continue

        try:
            tools = anyio.run(_list_tools, url, api_key)
        except Exception as e:  # noqa: BLE001
            log.warning(
                "No se pudo conectar al servidor MCP '%s' (%s): %s — el agente "
                "sigue arrancando sin esas tools", name, url, e,
            )
            continue

        for tool in tools:
            tool_id = f"{name}_{tool.name}" if multi else tool.name
            register(ToolDef(
                tool_id,
                tool.description or f"Tool '{tool.name}' del servidor MCP '{name}'.",
                f"mcp:{name}",
                tool.inputSchema or {"type": "object", "properties": {}},
                _make_handler(name, url, api_key, tool.name),
            ))
            total += 1

        log.info("Servidor MCP '%s': %d tool(s) registradas", name, len(tools))

    return total
