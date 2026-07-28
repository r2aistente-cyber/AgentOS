"""Registra las base tools al importar este paquete."""
from tools.base_tools import (  # noqa: F401
    file_tools, web_tools, memory_tools, exec_tools, git_tools, python_tools,
    skill_tools,
)

# Tools dinámicas descubiertas de servidores MCP (config.mcp_servers) — ver
# tools/mcp_client.py. Va después de las base_tools de arriba para que, si
# algún día un servidor MCP expone una tool con el mismo nombre que una
# base_tool, la base_tool ya registrada gane (discover_and_register no
# sobreescribe registros existentes por accidente — sí lo haría si el
# nombre choca, ver tools/registry.py:register, así que el orden importa).
from tools import mcp_client as _mcp_client
_mcp_client.discover_and_register()
