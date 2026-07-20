"""Tests de regresión para los 10 fixes del 2026-07-20.

Cada test fija un comportamiento que fue corregido:
  - MAX_TOOL_ROUNDS reducido a 5
  - Engine para el loop tras agotar rounds y pide resumen
  - Engine responde con mensaje de error en vez de crashear ante fallo del LLM
  - Historial limitado a 20 mensajes por llamada
  - tools/__init__.py registra las base tools al importarse
  - DSML siempre se limpia del contenido (no solo cuando no hay tool_calls)
  - is_confirmation_message reconoce palabras en castellano
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

_TEMPLATES = Path(__file__).resolve().parent.parent / "hub" / "templates"


# ─── Fixture: entorno de template aislado ─────────────────────────────────────

@pytest.fixture(autouse=True)
def _template_env(tmp_path):
    """Inyecta agent_config falso y agrega hub/templates al path."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _cfg = {
        "agent": {"name": "regression-agent", "port": 9999, "install_path": str(tmp_path)},
        "llm": {"provider": "mock", "model": "test-model", "num_ctx": 8192},
        "tools": {"allow": ["*"], "deny": []},
        "security": {"sandbox_paths": [str(data_dir)], "level": 1},
        "memory": {},
    }

    def _get(key, default=None):
        node = _cfg
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    mod = types.ModuleType("agent_config")
    mod.get = _get
    mod.get_secret = lambda _: None
    mod.AGENT_DIR = tmp_path
    mod.reload = lambda: None
    sys.modules["agent_config"] = mod

    if str(_TEMPLATES) not in sys.path:
        sys.path.insert(0, str(_TEMPLATES))

    yield mod

    sys.modules.pop("agent_config", None)
    for key in list(sys.modules):
        if key.startswith(("llm.", "tools.", "security.", "memory.", "rag.", "engine")):
            sys.modules.pop(key, None)
    for attr in ("llm", "tools", "security", "memory", "rag", "engine"):
        if attr in sys.modules and not getattr(sys.modules[attr], "__file__", None):
            sys.modules.pop(attr, None)
    if str(_TEMPLATES) in sys.path:
        sys.path.remove(str(_TEMPLATES))


# ─── Fixture: session store mockeada ─────────────────────────────────────────

@pytest.fixture
def mock_session():
    """Mock de memory.session para tests de engine que no necesitan DB real."""
    import uuid
    from unittest.mock import AsyncMock

    sid = str(uuid.uuid4())
    history_store: list[dict] = []

    async def create_session(user_id, title=""):
        return sid

    async def get_history(session_id, limit=30):
        return list(history_store[-limit:])

    async def add_message(session_id, role, content, tools_used=None, tokens=0):
        history_store.append({"role": role, "content": content})

    async def list_sessions(user_id, limit=20):
        return [{"id": sid, "title": "test", "created_at": "2026-01-01"}]

    with patch("memory.session.create_session", side_effect=create_session), \
         patch("memory.session.get_history", side_effect=get_history), \
         patch("memory.session.add_message", side_effect=add_message), \
         patch("memory.session.list_sessions", side_effect=list_sessions):
        yield {"session_id": sid, "history": history_store}


# ─── Fix: MAX_TOOL_ROUNDS = 5 ─────────────────────────────────────────────────

def test_max_tool_rounds_es_5():
    """Commit: fix: reducir MAX_TOOL_ROUNDS 10→5."""
    import importlib
    import engine
    importlib.reload(engine)
    assert engine.MAX_TOOL_ROUNDS == 5, (
        f"MAX_TOOL_ROUNDS debe ser 5, encontrado: {engine.MAX_TOOL_ROUNDS}"
    )


# ─── Fix: engine para el loop tras agotar rounds ──────────────────────────────

@pytest.mark.asyncio
async def test_engine_pide_resumen_al_agotar_tool_rounds(mock_session):
    """Commit: fix: DSML incomplete block leak + empty response after tool exhaustion.

    Cuando el LLM sigue retornando tool_calls después de MAX_TOOL_ROUNDS,
    el engine debe mandar un mensaje de resumen y obtener una respuesta final
    en texto plano.
    """
    from llm.adapter import LLMResponse, ToolCall

    call_count = 0
    final_answer = "Resumen final del agente."

    async def mock_chat(messages, tools=None, system=None):
        nonlocal call_count
        call_count += 1
        last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        # Siempre retorna tool_call hasta que el engine mande el mensaje de resumen
        if last and "Resume" in last.get("content", ""):
            return LLMResponse(content=final_answer, output_tokens=10)
        return LLMResponse(
            content="",
            tool_calls=[ToolCall(id=f"tc{call_count}", name="list_files", arguments={})],
            output_tokens=5,
        )

    mock_adapter = MagicMock()
    mock_adapter.chat = mock_chat

    with patch("llm.factory.build_adapter_with_fallback", return_value=mock_adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("haz algo con list_files repetidamente", session_id=None)

    assert result["reply"] == final_answer
    # Se llamó más veces que MAX_TOOL_ROUNDS (5 rounds + 1 resumen + posible vacío)
    assert call_count > 5


# ─── Fix: engine captura error del LLM sin crashear ───────────────────────────

@pytest.mark.asyncio
async def test_engine_captura_error_llm_sin_crashear(mock_session):
    """Commit: fix: engine atrapa errores LLM (500/503/400) en vez de crashear."""
    async def mock_chat_error(messages, tools=None, system=None):
        raise ConnectionError("503 Service Unavailable")

    mock_adapter = MagicMock()
    mock_adapter.chat = mock_chat_error

    with patch("llm.factory.build_adapter_with_fallback", return_value=mock_adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("hola", session_id=None)

    assert "session_id" in result
    assert "⚠️" in result["reply"] or "Error" in result["reply"], (
        "El engine debe retornar un mensaje de error, no crashear"
    )
    assert result["tokens_used"] == 0


# ─── Fix: historial limitado a 20 mensajes ────────────────────────────────────

@pytest.mark.asyncio
async def test_historial_limitado_a_20_mensajes(mock_session):
    """Commit: fix: limitar historial a últimos 20 mensajes por request.

    Tras guardar 30 mensajes en una sesión, el engine solo envía al LLM
    los últimos 20 (history[-20:]).
    """
    # Prellenar historial con 30 mensajes alternados user/assistant
    history = mock_session["history"]
    for i in range(15):
        history.append({"role": "user", "content": f"pregunta {i}"})
        history.append({"role": "assistant", "content": f"respuesta {i}"})

    mensajes_vistos: list[list[dict]] = []

    async def mock_chat(messages, tools=None, system=None):
        mensajes_vistos.append(list(messages))
        from llm.adapter import LLMResponse
        return LLMResponse(content="ok", output_tokens=5)

    mock_adapter = MagicMock()
    mock_adapter.chat = mock_chat

    with patch("llm.factory.build_adapter_with_fallback", return_value=mock_adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        await process_message("mensaje 31", session_id=mock_session["session_id"])

    assert mensajes_vistos, "El LLM debe haber sido llamado al menos una vez"
    # El primer call tiene los mensajes que el engine construyó; los últimos
    # son history[-20:] + el mensaje actual, así que ≤ 21 mensajes.
    primer_call = mensajes_vistos[0]
    assert len(primer_call) <= 21, (
        f"El engine envió {len(primer_call)} mensajes al LLM; el límite es 21 (20 historia + 1 actual)"
    )


# ─── Fix: tools/__init__.py registra base_tools ───────────────────────────────

def test_tools_init_registra_base_tools():
    """Commit: fix: tools/__init__.py debe importar base_tools para poblar el registry.

    Al importar el paquete `tools`, las tools base (read_file, write_file,
    list_files, search_files, save_memory, get_memory) deben estar registradas.
    """
    import tools  # noqa: F401  — ejecuta tools/__init__.py
    from tools import registry

    registered_names = {t.name for t in registry.all_tools()}
    expected = {"read_file", "write_file", "list_files", "search_files"}
    missing = expected - registered_names
    assert not missing, f"Tools no registradas después de importar `tools`: {missing}"


# ─── Fix: is_confirmation_message reconoce castellano ─────────────────────────

def test_is_confirmation_palabras_castellano():
    """Commit: fix: 7 bugs estructurales — flujo de confirmación."""
    from tools.orchestrator import is_confirmation_message

    palabras_ok = ["confirmar", "sí", "si", "adelante", "procede", "ok", "yes", "confirm"]
    for palabra in palabras_ok:
        assert is_confirmation_message(palabra), f"'{palabra}' debería ser confirmación"
        assert is_confirmation_message(f"  {palabra}  "), f"'{palabra}' con espacios debe funcionar"


def test_is_confirmation_rechaza_frases_parciales():
    """Frases que contienen una palabra de confirmación NO son confirmaciones."""
    from tools.orchestrator import is_confirmation_message

    no_confirmaciones = [
        "no confirmar",
        "quizás sí",
        "ok pero espera",
        "confirmación pendiente",
        "",
        "cancelar",
    ]
    for frase in no_confirmaciones:
        assert not is_confirmation_message(frase), f"'{frase}' NO debería ser confirmación"


# ─── Fix: DSML parsing (formato DeepSeek con pipes fullwidth U+FF5C) ──────────

def test_dsml_parse_bloque_completo_extrae_tool_call():
    """Commit: fix: DSML regex uses U+FF5C fullwidth pipes not ASCII pipes.

    _parse_dsml debe extraer correctamente una tool call de un bloque DSML completo
    usando el separador ｜｜ (U+FF5C) en vez de | ASCII.
    """
    from llm.openai_compat import _parse_dsml

    SEP = "｜｜"  # fullwidth vertical line U+FF5C
    dsml = (
        f"Texto previo.\n"
        f"<{SEP}DSML{SEP}tool_calls>\n"
        f"<{SEP}DSML{SEP}invoke name=\"list_files\">\n"
        f"<{SEP}DSML{SEP}parameter name=\"path\" string=\"true\">.</{ SEP}DSML{SEP}parameter>\n"
        f"</{SEP}DSML{SEP}invoke>\n"
        f"</{SEP}DSML{SEP}tool_calls>\n"
        f"Texto posterior."
    )

    clean, tool_calls = _parse_dsml(dsml)

    assert len(tool_calls) == 1
    assert tool_calls[0].name == "list_files"
    assert tool_calls[0].arguments.get("path") == "."
    assert f"<{SEP}DSML{SEP}" not in clean, "El DSML debe limpiarse del contenido"
    assert "Texto previo" in clean or "Texto posterior" in clean


def test_dsml_parse_bloque_incompleto_limpia_residuo():
    """Commit: fix: always strip DSML from content, not only when tool_calls is empty.

    Cuando el bloque DSML está truncado (sin cierre), _parse_dsml
    debe limpiar el residuo del contenido.
    """
    from llm.openai_compat import _parse_dsml

    SEP = "｜｜"
    # Bloque incompleto — sin tag de cierre
    truncated = f"Respuesta parcial.\n<{SEP}DSML{SEP}tool_calls>\n<{SEP}DSML{SEP}invoke name=\"list_files\">"

    clean, tool_calls = _parse_dsml(truncated)

    assert f"<{SEP}DSML{SEP}" not in clean, "Residuos DSML deben limpiarse aunque el bloque esté incompleto"


def test_dsml_has_dsml_con_pipes_ascii_falla():
    """Commit: fix: DSML regex uses U+FF5C fullwidth pipes not ASCII pipes.

    Un bloque con pipes ASCII (|) NO debe ser detectado como DSML.
    """
    from llm.openai_compat import _has_dsml

    # Pipe normal ASCII — NO es DSML de DeepSeek
    ascii_dsml = "<|DSML|tool_calls><|DSML|invoke name='x'></|DSML|invoke></|DSML|tool_calls>"
    assert not _has_dsml(ascii_dsml), (
        "Pipes ASCII no deben detectarse como DSML — solo funciona con U+FF5C"
    )


# ─── Fix: respuesta vacía fuerza segundo intento ──────────────────────────────

@pytest.mark.asyncio
async def test_engine_fuerza_respuesta_cuando_esta_vacia(mock_session):
    """Commit: fix: DSML incomplete block leak + empty response after tool exhaustion.

    Si el LLM retorna contenido vacío sin tool_calls, el engine hace un
    segundo intento pidiendo respuesta en texto plano.
    """
    from llm.adapter import LLMResponse

    call_count = 0

    async def mock_chat(messages, tools=None, system=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(content="", output_tokens=0)  # respuesta vacía
        return LLMResponse(content="Respuesta final tras reintento.", output_tokens=8)

    mock_adapter = MagicMock()
    mock_adapter.chat = mock_chat

    with patch("llm.factory.build_adapter_with_fallback", return_value=mock_adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("test", session_id=None)

    assert result["reply"] == "Respuesta final tras reintento."
    assert call_count == 2, "El engine debe haber hecho exactamente 2 llamadas al LLM"
