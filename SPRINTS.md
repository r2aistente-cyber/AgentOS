# 🏗️ R2 Core — Plan de desarrollo

> **Versión:** 1.0
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
✅ gh CLI autenticado (r2aistente-cyber)
```

Si todo está OK → arranca Fase 1.

---

## Fase 1 — Backend: Núcleo (días 1-3)

### 1.1 Proyecto base

```text
r2-autonomous/
├── backend/
│   ├── main.py                   ← FastAPI entry point
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

### 1.3 Tool Orchestrator

```text
backend/tools/
├── __init__.py
├── orchestrator.py               ← Ejecuta tools, valida permisos
├── registry.py                   ← Registro de tools disponibles
├── base_tools/
│   ├── file_tools.py             ← read, write, list, search
│   ├── web_tools.py              ← search, fetch
│   └── memory_tools.py           ← save, get, query
└── dev_tools/                    ← Solo R2 Core
    ├── github_tools.py           ← clone, PR, issues, commit
    ├── system_tools.py           ← exec, run_script (Nivel 3)
    └── build_tools.py            ← npm, build, test, deploy
```

**Archivos de referencia:** `DESIGN.md` sección 3 + `CONCEPTO.md` (R2 Core dev tools).

**Checklist:**
- [ ] ToolRegistry con registro y validación
- [ ] ToolOrchestrator.execute(name, args, user) → resultado
- [ ] Base tools: file_tools (read, write, list, search)
- [ ] Base tools: web_tools (search_web, fetch_url)
- [ ] Base tools: memory_tools (save_memory, get_memory, query_db)
- [ ] Dev tools: github_tools (clone, create_pr, commit_push, create_issue)
- [ ] Dev tools: system_tools (exec_command solo Nivel 3)
- [ ] Dev tools: build_tools (npm_install, run_build, run_tests)

### 1.4 Seguridad

```text
backend/security/
├── __init__.py
├── permissions.py                ← Niveles 0-3
├── sandbox.py                    ← Restricción de rutas
└── audit.py                      ← Log de auditoría (solo append)
```

**Archivos de referencia:** `DESIGN.md` sección 6 + APP.md sección 6.6 (caídas).

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

## Fase 2 — Backend: API endpoints (días 3-4)

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

## Fase 3 — Frontend webchat (días 4-5)

Chat web básico para que Xavier hable con R2 desde el navegador.

```text
frontend/
├── index.html
├── src/
│   ├── App.tsx
│   ├── Chat.tsx                  ← Burbujas de chat
│   ├── Input.tsx                 ← Input + enviar
│   └── api.ts                    ← Conexión a FastAPI
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

## Fase 4 — Integración WhatsApp (días 5-6)

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

## Fase 5 — App Tauri (días 7-9)

**Solo cuando el backend + webchat funcionan.** Sin apuro.

**Archivo de referencia:** `APP.md` (versión completa).

**Checklist:**
- [ ] Proyecto Tauri + React
- [ ] System tray icon + menú
- [ ] Ventana flotante (Cmd+Space)
- [ ] Conecta al backend local (localhost)
- [ ] Input + enviar desde app nativa
- [ ] Barra rápida de modelo (🧠 Qwen2.5:7b ▼)

---

## Resumen de entregables

```text
Fase 1 — Backend núcleo      → Día 3
  ✅ LLM adapter + tools natives
  ✅ Tool orchestrator + registry
  ✅ Base tools + dev tools (GitHub, exec)
  ✅ Seguridad + sandbox + auditoría
  ✅ Memoria + sesiones SQLite

Fase 2 — API endpoints        → Día 4
  ✅ POST /api/v1/chat funcionando
  ✅ Sesiones, archivos, modelos

Fase 3 — Webchat              → Día 5
  ✅ Xavier habla con R2 desde el navegador
  ✅ Sin terminal, sin comandos

Fase 4 — WhatsApp             → Día 6
  ✅ R2 también responde por WhatsApp

Fase 5 — App Tauri            → Día 9
  ✅ App nativa con icono y atajos
```

---

## Config inicial de R2 Core

```yaml
# config.yaml — R2 Core
profile: core
version: "1.0"

llm:
  provider: ollama
  model: qwen2.5:7b
  host: http://localhost:11434

channels:
  web: true
  whatsapp:
    enabled: true
    phone: "+57323249248068"

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
  dev:                        # Solo R2 Core
    - clone_repo
    - create_pr
    - commit_push
    - list_issues
    - create_issue
    - exec_command            # Nivel 3
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
  "version": "1.0",
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
