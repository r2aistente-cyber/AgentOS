# 🏗️ R2 Core — Plan de desarrollo

> **Versión:** 1.1
> **Prioridad:** Construir R2 Core (agente personal de Xavier) primero.
> **Desde R2 Core se derivan:** R2 Enterprise (clientes).
> **Metodología:** R2 (conceptos) → Trantor (desarrollo) → Terminus (pruebas).

---

## Fase 0 — Base técnica (día 0)

Trantor verifica que el entorno está listo:

```text
✅ Python 3.11+
✅ FastAPI instalado
✅ Ollama instalado y funcionando
✅ ollama pull qwen2.5:7b
✅ whatsapp-web.js (del proyecto anterior)
✅ GitHub API token en keychain (requests, no gh CLI)
```

Si todo está OK → arranca Fase 1.

---

## Fase 1 — Backend: Núcleo (días 1-3)

### 1.1 Proyecto base

```text
r2-autonomous/
├── backend/
│   ├── main.py                   ← FastAPI entry point (puerto 8234)
│   ├── config.py                 ← Lectura de config.yaml
│   ├── requirements.txt
│   └── ...
├── config.yaml                   ← Config de R2 Core
└── specialties/
    └── core.json                 ← Especialidad default (Xavier)
```

**Archivos de referencia:** `DESIGN.md` secciones 1-2-4.

### 1.2 LLM Adapter

```text
backend/llm/
├── __init__.py
├── adapter.py                    ← Clase abstracta LLMAdapter
├── ollama.py                     ← OllamaAdapter (tools nativos)
├── openai.py                     ← OpenAIAdapter (para después)
└── prompts.py                    ← Construcción de system prompt
```

**Archivos de referencia:** `DESIGN.md` sección 3.3 (function calling nativo).

**Checklist:**
- [ ] Clase abstracta con método `chat(messages, tools) → response`
- [ ] OllamaAdapter con tools nativos (no parseo JSON)
- [ ] System prompt builder (inyecta personalidad de core.json)

### 1.3 Tool Orchestrator — base tools

```text
backend/tools/
├── __init__.py
├── orchestrator.py               ← Ejecuta tools, valida permisos
├── registry.py                   ← Registro de tools disponibles
└── base_tools/
    ├── file_tools.py             ← read, write, list, search
    ├── web_tools.py              ← search, fetch
    └── memory_tools.py           ← save, get, query
```

**Archivos de referencia:** `DESIGN.md` sección 3 (function calling nativo).

**Checklist:**
- [ ] ToolRegistry con registro y validación
- [ ] ToolOrchestrator.execute(name, args, user) → resultado
- [ ] Base tools: file_tools (read, write, list, search)
- [ ] Base tools: web_tools (search_web, fetch_url)
- [ ] Base tools: memory_tools (save_memory, get_memory, query_db)

### 1.4 Seguridad

```text
backend/security/
├── __init__.py
├── permissions.py                ← Niveles 0-3
├── sandbox.py                    ← Restricción de rutas
└── audit.py                      ← Log de auditoría (solo append)
```

**Archivos de referencia:** `DESIGN.md` sección 6.

**Checklist:**
- [ ] PermissionEnforcer (Nivel 0-3)
- [ ] Sandbox con resolución de rutas
- [ ] ToolExecutionContext (user, level, session)
- [ ] Auditoría en SQLite (solo append)

### 1.5 Memoria y sesiones

```text
backend/memory/
├── __init__.py
├── db.py                         ← SQLite init + schema
├── session.py                    ← CRUD sesiones
└── models.py                     ← Data classes
```

**Archivos de referencia:** `DESIGN.md` sección 5 (DB schema).

**Checklist:**
- [ ] SQLite init con schema completo
- [ ] Session CRUD (crear, cargar, guardar, archivar)
- [ ] Historial de mensajes con paginación
- [ ] Memoria a largo plazo (clave-valor por usuario)

---

## Fase 1.5 — Dev tools: GitHub + sistema (días 3-4)

**Solo cuando el núcleo de Fase 1 esté estable y funcionando.**

### 1.5.1 Estructura

```text
backend/tools/dev_tools/          ← Solo R2 Core (Nivel 3)
├── github_tools.py               ← API REST con requests + token
├── system_tools.py               ← exec_command con whitelist estricta
└── build_tools.py                ← npm, pytest, build
```

### 1.5.2 GitHub tools — API REST (sin gh CLI)

gh CLI no está instalado en Trantor. Todo via `requests` + token del keychain.

```python
import requests

GITHUB_TOKEN = config.get_secret("github_token")  # keychain, no texto plano
GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def create_pr(repo, title, body, head, base="main"):
    r = requests.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=GITHUB_HEADERS,
        json={"title": title, "body": body, "head": head, "base": base}
    )
    return r.json()

def clone_repo(repo, dest):
    # git clone con token embebido en URL (no gh CLI)
    url = f"https://{GITHUB_TOKEN}@github.com/{repo}.git"
    subprocess.run(["git", "clone", url, dest], check=True)
```

**Checklist:**
- [ ] github_tools: clone_repo (git clone con token en URL)
- [ ] github_tools: list_issues, create_issue
- [ ] github_tools: create_pr, list_prs
- [ ] github_tools: commit_push (git add / commit / push)

### 1.5.3 exec_command — whitelist estricta

`exec_command` solo disponible en Nivel 3. Lista explícita de comandos permitidos.
Nada fuera de esta lista se ejecuta.

```python
# backend/tools/dev_tools/system_tools.py

EXEC_WHITELIST = {
    # Git
    "git": ["status", "add", "commit", "push", "pull",
            "log", "diff", "branch", "checkout", "merge", "clone"],
    # Node / npm
    "node": ["--version", "-e"],
    "npm": ["install", "run", "test", "build", "start", "ci"],
    "npx": ["*"],
    # Python
    "python": ["-m", "--version", "-c"],
    "pip": ["install", "list", "show", "freeze"],
    "pytest": ["*"],
    # Lectura / búsqueda
    "ls": ["*"], "cat": ["*"], "grep": ["*"],
    "find": ["*"], "echo": ["*"], "head": ["*"], "tail": ["*"],
    # Procesos
    "ps": ["aux", "-ef"],
    "kill": ["-9", "-15"],
    # Build
    "cargo": ["build", "test", "run", "check"],
    # Utilidades
    "which": ["*"], "pwd": [], "whoami": [],
}

# Patrones siempre bloqueados (antes de verificar whitelist)
EXEC_BLOCKED_PATTERNS = [
    "rm -rf",
    "sudo",
    "su ",
    "chmod 777",
    "curl | sh", "curl|sh",
    "wget | sh", "wget|sh",
    "bash <(",
    "mkfs",
    "dd if=",
    "> /dev/sda",
    "format c:",
    ":(){:|:&};:",   # fork bomb
]

def exec_command(command: str, cwd: str = None) -> dict:
    """
    Ejecuta un comando del sistema con whitelist estricta.
    Solo Nivel 3. Nunca sudo. Nunca rm -rf.
    """
    # 1. Bloquear patrones peligrosos primero
    cmd_lower = command.lower()
    for blocked in EXEC_BLOCKED_PATTERNS:
        if blocked in cmd_lower:
            return {"success": False, "error": f"Comando bloqueado: contiene '{blocked}'"}

    # 2. Parsear el binario principal
    parts = command.strip().split()
    binary = parts[0]

    # 3. Verificar que el binario está en whitelist
    if binary not in EXEC_WHITELIST:
        return {"success": False, "error": f"Binario '{binary}' no está en la whitelist"}

    # 4. Verificar subcomando si aplica
    allowed_args = EXEC_WHITELIST[binary]
    if allowed_args != ["*"] and len(parts) > 1:
        subcommand = parts[1]
        if subcommand not in allowed_args:
            return {
                "success": False,
                "error": f"'{binary} {subcommand}' no permitido. Permitidos: {allowed_args}"
            }

    # 5. Ejecutar en sandbox de directorios
    safe_cwd = sandbox.resolve_path(cwd) if cwd else Path.home()

    result = subprocess.run(
        parts,
        cwd=safe_cwd,
        capture_output=True,
        text=True,
        timeout=30
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout[:4096],   # truncar salidas largas
        "stderr": result.stderr[:1024],
        "returncode": result.returncode
    }
```

**Checklist:**
- [ ] system_tools: exec_command con whitelist + BLOCKED_PATTERNS
- [ ] build_tools: npm_install, run_build, run_tests, run_pytest
- [ ] Tests de seguridad: verificar que rm -rf / sudo fallan correctamente

---

## Fase 2 — Backend: API endpoints (días 4-5)

```text
backend/api/
├── __init__.py
├── chat.py                       ← POST /api/v1/chat (el principal)
├── sessions.py                   ← CRUD sesiones
├── files.py                      ← Upload / download
├── admin.py                      ← Usuarios, permisos
└── events.py                     ← Webhooks (para después)
```

**Checklist:**
- [ ] POST /api/v1/chat — el endpoint principal
- [ ] GET /api/v1/sessions — listar sesiones
- [ ] POST /api/v1/sessions/new — crear sesión
- [ ] POST /api/v1/upload — subir archivo
- [ ] GET /api/v1/files/{id} — descargar archivo
- [ ] GET /api/v1/admin/audit — ver log de auditoría
- [ ] GET /api/v1/models — lista modelos disponibles (de Ollama)

---

## Fase 3 — Frontend webchat (días 5-6)

Chat web básico para que Xavier hable con R2 desde el navegador.

```text
frontend/
├── index.html
├── src/
│   ├── App.tsx
│   ├── Chat.tsx                  ← Burbujas de chat
│   ├── Input.tsx                 ← Input + enviar
│   └── api.ts                    ← Conexión a FastAPI (:8234)
├── package.json
└── ...
```

**Checklist:**
- [ ] Chat con burbujas (como WhatsApp)
- [ ] Input de texto + botón enviar
- [ ] Conexión a POST /api/v1/chat
- [ ] Mostrar historial de la sesión
- [ ] Indicador de escritura (R2 está pensando...)
- [ ] Tool calls visibles (qué está haciendo R2)
- [ ] Drag & drop de archivos (subir y enviar al agente)

---

## Fase 4 — Integración WhatsApp (días 6-7)

```text
backend/channels/
├── __init__.py
├── base.py                       ← Channel abstracto
├── whatsapp.py                   ← whatsapp-web.js adapter
└── telegram.py                   ← Telegram adapter (después)
```

**Checklist:**
- [ ] Sidecar de WhatsApp (whatsapp-web.js)
- [ ] Recepción de mensajes → orquestador
- [ ] Envío de respuestas → WhatsApp
- [ ] Reconexión automática
- [ ] Sesión persistente (no pedir QR cada vez)

---

## Fase 5 — App Tauri (días 8-10)

**Solo cuando el backend + webchat funcionan.** Sin apuro.

**Archivo de referencia:** `APP.md` (versión completa).

**Checklist:**
- [ ] Proyecto Tauri + React
- [ ] System tray icon + menú
- [ ] Ventana flotante (Cmd+Space)
- [ ] Conecta al backend local (localhost:8234)
- [ ] Input + enviar desde app nativa
- [ ] Barra rápida de modelo (🧠 Qwen2.5:7b ▼)

---

## Resumen de entregables

```text
Fase 1   — Backend núcleo         → Día 3
  ✅ LLM adapter (function calling nativo)
  ✅ Tool orchestrator + base tools
  ✅ Seguridad + sandbox + auditoría
  ✅ Memoria + sesiones SQLite

Fase 1.5 — Dev tools              → Día 4
  ✅ GitHub tools (API REST, sin gh CLI)
  ✅ exec_command con whitelist estricta
  ✅ Build tools (npm, pytest)

Fase 2   — API endpoints          → Día 5
  ✅ POST /api/v1/chat funcionando
  ✅ Sesiones, archivos, modelos

Fase 3   — Webchat                → Día 6
  ✅ Xavier habla con R2 desde el navegador
  ✅ Sin terminal, sin comandos

Fase 4   — WhatsApp               → Día 7
  ✅ R2 también responde por WhatsApp

Fase 5   — App Tauri              → Día 10
  ✅ App nativa con icono y atajos
```

---

## Config inicial de R2 Core

```yaml
# config.yaml — R2 Core
profile: core
version: "1.1"

server:
  port: 8234

llm:
  provider: ollama
  model: qwen2.5:7b
  host: http://localhost:11434

channels:
  web: true
  whatsapp:
    enabled: true
    phone: "+573192270876"

security:
  default_level: 3
  sandbox_paths:
    - ~/Trantor/
    - ~/Documents/
    - ~/r2-autonomous/
    - /tmp/

tools:
  base:
    - read_file
    - write_file
    - list_files
    - search_web
    - fetch_url
    - save_memory
    - get_memory
  dev:                        # Solo R2 Core (Nivel 3)
    - clone_repo
    - create_pr
    - commit_push
    - list_issues
    - create_issue
    - exec_command            # Whitelist estricta — ver Fase 1.5
    - npm_install
    - run_build
    - run_tests
  comms:
    - send_whatsapp

specialty: core
```

```json
{
  "id": "core",
  "name": "R2 Core",
  "version": "1.1",
  "personality": {
    "system_prompt": "Eres R2, un asistente personal y arquitecto de software...",
    "tone": "directo",
    "humor": "sarcástico",
    "empathy": "leal"
  },
  "model": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "temperature": 0.7
  },
  "tools": {
    "allow": ["*"]
  },
  "sandbox": {
    "paths": ["~/Trantor/", "~/Documents/", "~/r2-autonomous/", "/tmp/"]
  }
}
```
