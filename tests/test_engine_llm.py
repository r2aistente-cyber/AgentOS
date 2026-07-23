"""Tests del Engine multi-LLM: adaptadores, traducción Anthropic y process_message."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _template_support import (  # noqa: E402
    TEMPLATES_DIR as _TEMPLATES,
    default_config,
    install_agent_config,
    cleanup_template_modules,
)


@pytest.fixture(autouse=True)
def mock_agent_config(tmp_path):
    """Inyecta agent_config falso y agrega el dir de templates al path."""
    cfg = default_config(tmp_path)
    cfg["llm"].update({"temperature": 0.7, "max_tokens": 512})
    mod = install_agent_config(tmp_path, cfg)

    yield mod

    cleanup_template_modules()


# ── MockAdapter ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_adapter_ping():
    from llm.mock import MockAdapter
    assert await MockAdapter().ping() is True


@pytest.mark.asyncio
async def test_mock_adapter_echo_sin_tools():
    from llm.mock import MockAdapter
    resp = await MockAdapter().chat([{"role": "user", "content": "hola"}])
    assert "hola" in resp.content
    assert not resp.has_tool_calls


@pytest.mark.asyncio
async def test_mock_adapter_llama_tool_si_nombre_en_mensaje():
    from llm.mock import MockAdapter
    tools = [{"function": {"name": "file_read", "description": "lee archivos"}}]
    resp = await MockAdapter().chat(
        [{"role": "user", "content": "usa file_read por favor"}],
        tools=tools,
    )
    assert resp.has_tool_calls
    assert resp.tool_calls[0].name == "file_read"


@pytest.mark.asyncio
async def test_mock_adapter_no_repite_tool_si_ya_hay_tool_result():
    from llm.mock import MockAdapter
    tools = [{"function": {"name": "file_read", "description": "lee archivos"}}]
    messages = [
        {"role": "user", "content": "usa file_read"},
        {"role": "tool", "tool_call_id": "x", "content": "resultado"},
    ]
    resp = await MockAdapter().chat(messages, tools=tools)
    assert not resp.has_tool_calls


# ── LLM factory ──────────────────────────────────────────────────────────────

def test_build_adapter_mock():
    from llm.factory import build_adapter
    from llm.mock import MockAdapter
    adapter = build_adapter()
    assert isinstance(adapter, MockAdapter)


def test_build_adapter_proveedor_desconocido(mock_agent_config):
    mock_agent_config.get = lambda key, default=None: (
        "inexistente" if key == "llm.provider" else default
    )
    import importlib
    import sys
    # Forzar re-import para que factory vea el agent_config mockeado
    sys.modules.pop("llm.factory", None)
    if "llm" in sys.modules:
        sys.modules["llm"].__dict__.pop("factory", None)
    import llm.factory as factory  # `import x.y` garantiza sys.modules["llm.factory"]
    importlib.reload(factory)
    with pytest.raises(ValueError, match="desconocido"):
        factory.build_adapter()


# ── Traducción Anthropic ─────────────────────────────────────────────────────

def test_to_anthropic_tools_traduce_parameters():
    from llm.anthropic import _to_anthropic_tools
    tools = [{"function": {
        "name": "mi_tool",
        "description": "hace algo",
        "parameters": {"type": "object", "properties": {"x": {"type": "string"}}},
    }}]
    result = _to_anthropic_tools(tools)
    assert result[0]["name"] == "mi_tool"
    assert "input_schema" in result[0]
    assert result[0]["input_schema"]["type"] == "object"


def test_to_anthropic_messages_convierte_user():
    from llm.anthropic import _to_anthropic_messages
    result = _to_anthropic_messages([{"role": "user", "content": "hola"}])
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "hola"


def test_to_anthropic_messages_convierte_assistant():
    from llm.anthropic import _to_anthropic_messages
    msgs = [{"role": "assistant", "content": "bien"}]
    result = _to_anthropic_messages(msgs)
    assert result[0]["role"] == "assistant"
    blocks = result[0]["content"]
    assert any(b.get("text") == "bien" for b in blocks)


def test_to_anthropic_messages_agrupa_tool_results():
    """Los role=tool deben agruparse como bloque user con type=tool_result."""
    from llm.anthropic import _to_anthropic_messages
    msgs = [
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "t1", "function": {"name": "mi_fn", "arguments": {}}}
        ]},
        {"role": "tool", "tool_call_id": "t1", "content": "resultado A"},
        {"role": "tool", "tool_call_id": "t2", "content": "resultado B"},
    ]
    result = _to_anthropic_messages(msgs)
    # El último mensaje debe ser role=user con los tool_results
    last = result[-1]
    assert last["role"] == "user"
    types_ = [b["type"] for b in last["content"]]
    assert types_.count("tool_result") == 2


def test_to_anthropic_messages_tool_calls_en_assistant():
    from llm.anthropic import _to_anthropic_messages
    msgs = [
        {"role": "user", "content": "llama la tool"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "tc1", "type": "function",
             "function": {"name": "buscar", "arguments": {"q": "python"}}}
        ]},
    ]
    result = _to_anthropic_messages(msgs)
    asst = next(m for m in result if m["role"] == "assistant")
    tool_use = next(b for b in asst["content"] if b["type"] == "tool_use")
    assert tool_use["name"] == "buscar"
    assert tool_use["input"] == {"q": "python"}


# ── Engine process_message (E2E con mock) ────────────────────────────────────

@pytest.mark.asyncio
async def test_process_message_retorna_reply(tmp_path):
    import hub.templates.memory.db as db_mod
    import importlib

    # DB en tmp_path
    db_file = tmp_path / "memory.db"
    import hub.templates.memory.db as _db

    # Cargar el engine usando las rutas del template
    sys.path.insert(0, str(_TEMPLATES))
    try:
        import memory.db as mem_db
        # Patch para usar DB temporal
        original = mem_db._DB_PATH if hasattr(mem_db, "_DB_PATH") else None
        mem_db._DB_PATH = db_file
        await mem_db.init_db()

        from engine import process_message
        result = await process_message("hola mundo", session_id=None)

        assert "session_id" in result
        assert "hola mundo" in result["reply"] or result["reply"]  # mock devuelve eco
    finally:
        # Limpiar módulos engine
        for key in list(sys.modules):
            if key in ("engine", "memory.db", "memory.session") or key.startswith(("llm.", "tools.", "security.", "memory.")):
                sys.modules.pop(key, None)
        if str(_TEMPLATES) in sys.path:
            sys.path.remove(str(_TEMPLATES))


@pytest.mark.asyncio
async def test_process_message_sesion_nueva_si_none(tmp_path):
    import memory.db as mem_db
    db_file = tmp_path / "memory2.db"
    mem_db._DB_PATH = db_file
    await mem_db.init_db()

    from engine import process_message
    r1 = await process_message("ping", session_id=None)
    r2 = await process_message("pong", session_id=None)
    # Cada llamada sin session_id crea una sesión nueva
    assert r1["session_id"] != r2["session_id"]
