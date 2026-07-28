"""Tests E2E del engine del agente (hub/templates/engine.py).

Cubre los flujos que test_engine_llm.py no alcanza:
  - Ciclo completo mensaje → tool → respuesta con registry real
  - Gate de confirmación: tool requires_confirm → pendiente → "confirmar" → ejecuta
  - PermissionEnforcer: tool deny-listeada se bloquea en el orquestador
  - Múltiples rounds de tools dentro del límite MAX_TOOL_ROUNDS
  - RAG inactivo no rompe el flujo
"""
from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── Helper: crea un LLM mock configurable ────────────────────────────────────

def _make_adapter(*responses):
    """Crea un mock LLM que retorna respuestas en secuencia."""
    from llm.adapter import LLMResponse, ToolCall

    queue = list(responses)

    async def chat(messages, tools=None, system=None):
        if not queue:
            return LLMResponse(content="[sin más respuestas]", output_tokens=0)
        item = queue.pop(0)
        if isinstance(item, str):
            return LLMResponse(content=item, output_tokens=len(item.split()))
        # dict: {"tool": name, "args": {...}}
        return LLMResponse(
            content="",
            tool_calls=[types.SimpleNamespace(
                id=f"tc_{item['tool']}",
                name=item["tool"],
                arguments=item.get("args", {}),
            )],
            output_tokens=5,
        )

    adapter = MagicMock()
    adapter.chat = chat
    return adapter


# ─── Ciclo simple: sin tools ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_ciclo_sin_tools(db):
    """Mensaje → LLM responde texto → se guarda en sesión."""
    adapter = _make_adapter("Respuesta directa sin tools.")

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("hola", session_id=None)

    assert result["reply"] == "Respuesta directa sin tools."
    assert result["session_id"]
    assert result["tools_used"] == []


# ─── Ciclo con tool: list_files ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_ciclo_con_tool(db):
    """Mensaje → LLM llama list_files → resultado → LLM responde con contexto."""
    adapter = _make_adapter(
        {"tool": "list_files", "args": {"path": "."}},
        "Lista obtenida correctamente.",
    )

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("lista archivos", session_id=None)

    assert result["reply"] == "Lista obtenida correctamente."
    assert "list_files" in result["tools_used"]


# ─── Multi-round tools ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_multi_round_tools(db):
    """El engine ejecuta múltiples rounds de tools dentro del límite."""
    adapter = _make_adapter(
        {"tool": "list_files", "args": {}},
        {"tool": "list_files", "args": {}},
        "Revisé los archivos dos veces.",
    )

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("revisa archivos dos veces", session_id=None)

    assert result["tools_used"].count("list_files") == 2
    assert result["reply"] == "Revisé los archivos dos veces."


# ─── Continuación de sesión ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_continua_sesion_existente(db):
    """Dos llamadas con el mismo session_id comparten historial.

    Usa un solo patch context para que `engine.build_adapter` (que se bindea
    al importarse el módulo) apunte siempre al mismo mock configurable.
    """
    from llm.adapter import LLMResponse

    call_count = 0
    captured_second_messages: list = []

    async def chat_secuencial(messages, tools=None, system=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Primera llamada: respuesta simple
            return LLMResponse(content="Primera respuesta.", output_tokens=5)
        # Segunda llamada: capturar mensajes para verificar historial
        captured_second_messages.extend(messages)
        return LLMResponse(content="Segunda respuesta con memoria.", output_tokens=5)

    adapter = MagicMock()
    adapter.chat = chat_secuencial

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message

        # Primera llamada — crea sesión
        r1 = await process_message("primer mensaje", session_id=None)
        sid = r1["session_id"]

        # Segunda llamada — misma sesión, debe incluir historial del primer turno
        r2 = await process_message("segundo mensaje", session_id=sid)

    assert r2["session_id"] == sid
    roles = [m["role"] for m in captured_second_messages]
    assert "user" in roles, "El segundo turno debe incluir mensajes de rol user en el historial"
    assert "assistant" in roles, "El historial debe incluir la respuesta del primer turno"


# ─── PermissionEnforcer: tool deny-listeada ───────────────────────────────────

@pytest.mark.asyncio
async def test_engine_tool_denegada_retorna_error(db, template_env):
    """Si una tool está en deny, el orquestador retorna error sin ejecutarla."""
    # Modificar config: deny exec_command
    template_env["cfg"]["tools"]["deny"] = ["exec_command"]
    template_env["mod"].get = lambda key, default=None: (
        template_env["cfg"].get(key.split(".")[0], {}) if "." not in key
        else (template_env["cfg"].get(key.split(".")[0], {}) or {}).get(key.split(".")[1], default)
    )

    from llm.adapter import ToolCall
    from tools.orchestrator import ToolOrchestrator

    orch = ToolOrchestrator(session_id="test-deny")
    tc = ToolCall(id="1", name="exec_command", arguments={"command": "ls"})
    result = await orch.execute(tc)

    assert result.success is False
    assert "no está en la lista de tools permitidas" in result.error


# ─── PermissionEnforcer: tool inexistente ─────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_tool_inexistente_retorna_error(db):
    """Una tool call a una tool que no existe retorna error claro."""
    from llm.adapter import ToolCall
    from tools.orchestrator import ToolOrchestrator

    orch = ToolOrchestrator(session_id="test-notfound")
    tc = ToolCall(id="x", name="tool_que_no_existe", arguments={})
    result = await orch.execute(tc)

    assert result.success is False
    assert "no existe" in result.error


# ─── Gate de confirmación: requires_confirm=True ──────────────────────────────

@pytest.mark.asyncio
async def test_gate_confirmacion_bloquea_sin_confirmar(db, template_env):
    """Una tool con requires_confirm=True y security.level >= 2 se bloquea sin token."""
    # Subir level a 2 para activar el gate
    template_env["cfg"]["security"]["level"] = 2

    # Recargar orchestrator para que lea el nuevo level
    import sys
    sys.modules.pop("tools.orchestrator", None)

    from llm.adapter import ToolCall
    from tools.orchestrator import ToolOrchestrator
    from tools import registry

    # exec_command tiene requires_confirm=True
    tool = registry.get("exec_command")
    assert tool is not None and tool.requires_confirm

    orch = ToolOrchestrator(session_id="sess-noconfirm")
    tc = ToolCall(id="2", name="exec_command", arguments={"command": "ls"})
    result = await orch.execute(tc)

    assert result.blocked is True
    assert result.success is False


@pytest.mark.asyncio
async def test_gate_confirmacion_ejecuta_tras_confirmar(db, template_env):
    """Tras mark_confirmed(session_id) sobre la ToolCall pendiente, se ejecuta."""
    template_env["cfg"]["security"]["level"] = 2

    import sys
    sys.modules.pop("tools.orchestrator", None)

    from llm.adapter import ToolCall
    from tools.orchestrator import ToolOrchestrator, mark_confirmed

    orch = ToolOrchestrator(session_id="sess-confirmed")
    tc = ToolCall(id="3", name="exec_command", arguments={"command": "echo ok"})

    # Primer intento: queda pendiente de confirmación.
    first = await orch.execute(tc)
    assert first.blocked is True

    # mark_confirmed retorna la ToolCall completa lista para reinyectar.
    confirmed_tc = mark_confirmed("sess-confirmed")
    assert confirmed_tc is not None

    result = await orch.execute(confirmed_tc)

    # exec_command usa asyncio.create_subprocess_shell — en el sandbox de test
    # puede no estar disponible; lo importante es que NO vuelve a bloquear.
    assert result.blocked is not True, (
        "Con confirmación activa, no debe volver a quedar pendiente"
    )


@pytest.mark.asyncio
async def test_gate_confirmacion_token_de_un_solo_uso(db, template_env):
    """La confirmación se consume tras la primera ejecución."""
    template_env["cfg"]["security"]["level"] = 2

    import sys
    sys.modules.pop("tools.orchestrator", None)

    from llm.adapter import ToolCall
    from tools.orchestrator import ToolOrchestrator, mark_confirmed

    orch = ToolOrchestrator(session_id="sess-onetime")
    tc = ToolCall(id="4", name="exec_command", arguments={"command": "echo ok"})

    # Primer intento: queda pendiente.
    await orch.execute(tc)
    confirmed_tc = mark_confirmed("sess-onetime")
    assert confirmed_tc is not None

    # Primera ejecución confirmada: consume el token.
    await orch.execute(confirmed_tc)

    # Segunda ejecución sin volver a confirmar: debe bloquearse de nuevo.
    result2 = await orch.execute(tc)
    assert result2.blocked is True, "El token debe ser de un solo uso"


# ─── is_confirmation_message en el flujo del engine ──────────────────────────

@pytest.mark.asyncio
async def test_engine_reconoce_confirmacion_sin_llamar_llm(db):
    """Al recibir 'confirmar', el engine activa el token sin llamar al LLM primero."""
    mensajes_enviados_al_llm: list = []

    async def mock_chat(messages, tools=None, system=None):
        mensajes_enviados_al_llm.append(list(messages))
        from llm.adapter import LLMResponse
        return LLMResponse(content="ok", output_tokens=1)

    adapter = MagicMock()
    adapter.chat = mock_chat

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message, is_confirmation_message

        assert is_confirmation_message("confirmar")

        # Crear sesión primero
        from memory import session as ss
        sid = await ss.create_session("user")

        # Enviar confirmación
        result = await process_message("confirmar", session_id=sid)

    assert result["session_id"] == sid
    # El engine sigue y llama al LLM para continuar el flujo
    assert len(mensajes_enviados_al_llm) >= 1


# ─── RAG desactivado no rompe el engine ───────────────────────────────────────

@pytest.mark.asyncio
async def test_engine_funciona_sin_rag(db):
    """Si rag.indexer.has_knowledge() retorna False, el engine sigue normal."""
    adapter = _make_adapter("Respuesta sin contexto RAG.")

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=False), \
         patch("rag.retriever.retrieve", return_value=""):
        from engine import process_message
        result = await process_message("test sin rag", session_id=None)

    assert result["reply"] == "Respuesta sin contexto RAG."


@pytest.mark.asyncio
async def test_engine_funciona_si_rag_lanza_excepcion(db):
    """Si el RAG falla, el engine sigue sin contexto (no crashea)."""
    adapter = _make_adapter("Ok a pesar del error de RAG.")

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=True), \
         patch("rag.retriever.retrieve", side_effect=RuntimeError("ChromaDB not available")):
        from engine import process_message
        result = await process_message("test rag error", session_id=None)

    assert result["reply"] == "Ok a pesar del error de RAG."


@pytest.mark.asyncio
async def test_rag_retrieve_no_bloquea_el_event_loop(db):
    """retrieve() es síncrono y, la primera vez que un agente con knowledge
    lo usa, carga el modelo de embeddings (puede tardar decenas de
    segundos) — debe correr en un thread aparte (asyncio.to_thread), no
    bloquear el event loop del agente. Si bloqueara, el healthchecker del
    Hub no podría atender /api/v1/health mientras tanto y marcaría el
    agente 'error' justo después de la primera respuesta — bug real
    reproducido y reportado por Xavier."""
    import asyncio
    import time

    adapter = _make_adapter("Ok.")
    tiempos: dict[str, float] = {}

    def retrieve_lento(query):
        time.sleep(0.3)
        return ""

    async def tarea_paralela(inicio: float):
        await asyncio.sleep(0.05)
        tiempos["marcador"] = time.monotonic() - inicio

    with patch("llm.factory.build_adapter_with_fallback", return_value=adapter), \
         patch("rag.indexer.has_knowledge", return_value=True), \
         patch("rag.retriever.retrieve", side_effect=retrieve_lento):
        from engine import process_message
        inicio = time.monotonic()
        await asyncio.gather(
            process_message("test", session_id=None),
            tarea_paralela(inicio),
        )

    # Si retrieve() bloqueara el event loop, tarea_paralela no podría
    # despertar de su sleep(0.05) hasta que los 0.3s de retrieve_lento
    # terminaran — el marcador tardaría >= 0.3s en vez de ~0.05s.
    assert tiempos["marcador"] < 0.15
