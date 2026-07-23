"""Helpers compartidos para testear hub/templates/ como si fuera el paquete
de un agente real: agent_config falso + hub/templates en sys.path.

Antes este patrón (~30 líneas) estaba copiado en 6 archivos de test
distintos (tests/template/conftest.py, test_engine_llm.py,
test_engine_regression.py, test_security.py, test_sessions.py,
test_files.py). Una de esas copias tenía un bug real de aislamiento
(ver cleanup_template_modules) que existía simultáneamente en varias
copias — motivo suficiente para consolidarlo en un solo lugar.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "hub" / "templates"

_ENGINE_PREFIXES = ("llm.", "tools.", "security.", "memory.", "rag.", "engine")
_ENGINE_PACKAGES = ("llm", "tools", "security", "memory", "rag", "engine")


def default_config(tmp_path: Path) -> dict[str, Any]:
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    return {
        "agent": {"name": "test-agent", "port": 9999, "install_path": str(tmp_path)},
        "llm": {"provider": "mock", "model": "test-model", "num_ctx": 8192},
        "tools": {"allow": ["*"], "deny": []},
        "security": {"sandbox_paths": [str(data_dir)]},
        "memory": {},
        "hub": {"port": 8234},
    }


def install_agent_config(tmp_path: Path, cfg: dict[str, Any] | None = None) -> types.ModuleType:
    """Instala un módulo `agent_config` falso en sys.modules y agrega
    hub/templates a sys.path.

    Retorna el módulo instalado; `mod._cfg` es el dict de config mutable
    en vivo — algunos tests necesitan cambiarlo a mitad de test (ej. subir
    `security.level` y forzar un re-import de tools.orchestrator).
    """
    if cfg is None:
        cfg = default_config(tmp_path)

    def _get(key, default=None):
        node = cfg
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    mod = types.ModuleType("agent_config")
    mod.get = _get
    mod.get_secret = lambda _key: None
    mod.AGENT_DIR = tmp_path
    mod.reload = lambda: None
    mod._cfg = cfg
    sys.modules["agent_config"] = mod

    if str(TEMPLATES_DIR) not in sys.path:
        sys.path.insert(0, str(TEMPLATES_DIR))
    return mod


def cleanup_template_modules() -> None:
    """Deshace install_agent_config(): saca agent_config, agent_main y todos
    los submódulos/paquetes del engine de sys.modules, y quita hub/templates
    de sys.path.

    Los paquetes base (tools, llm, security, memory, rag, engine) se borran
    SIEMPRE, no solo cuando "parecen" stubs sin __file__: si quedan
    cacheados, `from tools import registry` puede resolver el atributo
    stale del paquete en vez de reimportar el submódulo recién borrado,
    desincronizando _REGISTRY entre tests (dos módulos "tools.registry"
    objeto-distintos coexistiendo — visto en producción durante este fix).
    """
    sys.modules.pop("agent_config", None)
    sys.modules.pop("agent_main", None)
    for key in list(sys.modules):
        if key.startswith(_ENGINE_PREFIXES):
            sys.modules.pop(key, None)
    for pkg in _ENGINE_PACKAGES:
        sys.modules.pop(pkg, None)
    if str(TEMPLATES_DIR) in sys.path:
        sys.path.remove(str(TEMPLATES_DIR))
