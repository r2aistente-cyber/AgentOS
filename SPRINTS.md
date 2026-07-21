# 🏗️ R2 Hub — Plan de Desarrollo v2.0

> **Versión:** 2.0  
> **Arquitectura:** Hub + Agentes Independientes  
> **Prioridad:** Primero el Hub + engine template, luego los agentes

---

## 📋 Resumen de Fases

```text
Sprint 1  — Hub: gestión de agentes (3 días)
Sprint 2  — Engine base + LLM + tools (3 días)
Sprint 3  — Frontend: dashboard + wizard (4 días)
Sprint 4  — Logs, monitoreo, auto-restart (2 días)
Sprint 5  — Primer agente: R2 PRIME (1 día)
Sprint 6  — Canales: WhatsApp por agente (2 días)
Sprint 7  — Empaquetado + instalador (2 días)

Total: ~17 días para MVP con 1 agente funcional
```

---

## Sprint 1 — Hub: Gestión de Agentes (3 días)

### Objetivo
El Hub puede crear, listar, iniciar y detener agentes como procesos independientes.

### 1.1 Estructura del Hub

```text
r2-autonomous/hub/
├── main.py                       ← FastAPI :8234
├── config.py                     ← Config del Hub
├── requirements.txt              ← Dependencias
│
├── agent_manager.py              ← Crear, configurar, eliminar
├── agent_process.py              ← Subprocesos: start/stop/restart
├── health_checker.py             ← Health checks periódicos
│
├── api/
│   ├── __init__.py
│   ├── agents.py                 ← CRUD agentes
│   └── admin.py                  ← Config del Hub
│
└── templates/                    ← Plantillas para nuevos agentes
    ├── agent_main.py             ← Engine base (FastAPI)
    ├── default_config.yaml       ← Config base
    └── run.sh                    ← Script para lanzar agente
```

### Checklist

- [x] `hub/main.py` — FastAPI con CORS, middleware
- [x] `hub/config.py` — Carga `config.yaml` del Hub
- [x] `hub/agent_manager.py`:
  - [x] `create(name, config) → AgentInfo`
  - [x] `delete(name)` — stop + archivar directorio
  - [x] `list() → list[AgentInfo]`
  - [x] `get(name) → AgentInfo`
  - [x] `get_config(name) → dict`
  - [x] `update_config(name, config)` — requiere restart
- [x] `hub/agent_process.py`:
  - [x] `AgentProcess.start()` — lanza uvicorn como subproceso
  - [x] `AgentProcess.stop()` — SIGTERM + timeout + SIGKILL
  - [x] `AgentProcess.restart()` — stop + start
  - [x] `AgentProcess.is_alive` — property
  - [x] `AgentProcess._wait_ready(timeout)` — espera health check
- [x] `hub/health_checker.py`:
  - [x] Loop async que verifica agentes cada N segundos
  - [x] Auto-restart en agentes con `auto_restart: true`
- [x] `hub/api/agents.py`:
  - [x] `GET  /api/v1/hub/agents` — lista agentes
  - [x] `POST /api/v1/hub/agents` — crea agente
  - [x] `DELETE /api/v1/hub/agents/{name}` — elimina
  - [x] `POST /api/v1/hub/agents/{name}/start`
  - [x] `POST /api/v1/hub/agents/{name}/stop`
  - [x] `POST /api/v1/hub/agents/{name}/restart`
  - [x] `GET  /api/v1/hub/agents/{name}/config`
  - [x] `PUT  /api/v1/hub/agents/{name}/config`
- [x] `hub/templates/agent_main.py` — esqueleto base (solo health check + chat stub)
- [x] `hub/templates/default_config.yaml` — config base con defaults
- [x] Probar: crear agente → iniciar → health check OK → detener  ✅ smoke test E2E OK (17 Jul 2026)

---

## Sprint 2 — Engine Base + LLM + Tools (3 días)

### Objetivo
El template `agent_main.py` tiene LLM, tools y memoria funcionales. Cada agente puede conversar.

### 2.1 Lo que se reutiliza de la v1

Del código existente que se puede reutilizar SIN CAMBIOS:

```text
backend/llm/adapter.py        → hub/templates/llm/adapter.py
backend/llm/ollama.py         → hub/templates/llm/ollama.py
backend/llm/prompts.py        → hub/templates/llm/prompts.py

backend/tools/orchestrator.py → hub/templates/tools/orchestrator.py
backend/tools/registry.py     → hub/templates/tools/registry.py
backend/tools/base_tools/     → hub/templates/tools/base_tools/

backend/security/sandbox.py   → hub/templates/security/sandbox.py
backend/security/permissions.py → hub/templates/security/permissions.py
backend/security/audit.py     → hub/templates/security/audit.py

backend/memory/db.py          → hub/templates/memory/db.py
backend/memory/session.py     → hub/templates/memory/session.py
```

**Concepto: los templates son copias.** Cada nuevo agente recibe su propia copia de estos archivos. Así puede modificar tools, seguridad o memoria sin afectar a otros.

### 2.2 Estructura del template

```text
hub/templates/
├── agent_main.py              ← Entry point (FastAPI)
├── default_config.yaml        ← Config base
├── run.sh                     ← Script de inicio
│
├── llm/                       ← Código copiado de v1
│   ├── adapter.py
│   ├── ollama.py
│   └── prompts.py
│
├── tools/                     ← Código copiado de v1
│   ├── orchestrator.py
│   ├── registry.py
│   └── base_tools/
│       ├── file_tools.py
│       ├── web_tools.py
│       └── memory_tools.py
│
├── security/
│   ├── sandbox.py
│   ├── permissions.py
│   └── audit.py
│
└── memory/
    ├── db.py
    └── session.py
```

### Checklist

- [x] Copiar y adaptar archivos de v1 a `hub/templates/` (imports locales, config por agente)
- [x] `agent_main.py` completo con:
  - [x] Carga de config.yaml (incluyendo api_key y provider)
  - [x] LLMAdapter multi-proveedor: Ollama (local), OpenAI, Anthropic (Claude), OpenCode, Custom + Mock (dev/test). *(Google pendiente)*
  - [x] API keys vía `get_secret` (env, nunca texto plano)
  - [x] ToolRegistry + ToolOrchestrator
  - [x] Database + SessionManager (SQLite por agente)
  - [x] Sandbox + PermissionEnforcer (por agente) + Audit
  - [x] `POST /api/v1/chat` funcional
  - [x] `GET  /api/v1/health` funcional
  - [x] `GET  /api/v1/sessions` funcional
- [x] `POST /api/v1/upload` — subir archivos al data/ del agente
- [x] `GET  /api/v1/files` — listar archivos
- [ ] Procesamiento de adjuntos: PDF, DOCX, TXT, CSV, XLSX, imágenes, audio *(pendiente: hoy solo se guardan; falta extracción de contenido)*
- [x] Probar: crear agente → iniciar → enviar mensaje → recibe respuesta ✅ smoke test E2E (mock)
- [x] Probar: LLM llama tool → ejecuta → devuelve resultado ✅
- [x] Probar: tools denegadas no se ejecutan ✅ (allow/deny por agente en PermissionEnforcer)

---

## Sprint 3 — Frontend: Dashboard + Wizard (4 días)

### Objetivo
Interfaz web para gestionar agentes desde el navegador.

### 3.1 Estructura

```text
r2-autonomous/frontend/
├── index.html
├── src/
│   ├── App.tsx
│   ├── Dashboard.tsx            ← Lista de agentes con estado
│   ├── CreateWizard.tsx         ← Wizard paso a paso
│   ├── AgentDetail.tsx          ← Detalle + acciones (start/stop)
│   ├── ChatView.tsx             ← Chat con el agente seleccionado
│   ├── LogsView.tsx             ← Logs en vivo
│   ├── api.ts                   ← Conexión al Hub (:8234)
│   └── components/
│       ├── StatusBadge.tsx      ← 🟢🔴 indicator
│       ├── AgentCard.tsx        ← Card de agente
│       └── ...
├── package.json
└── ...
```

### 3.2 Dashboard

```
┌──────────────────────────────────────────────────────┐
│  🏠 R2 Hub                   [+ Crear Agente]       │
│                                                      │
│  ┌─────────────────────────────────────────────────┐ │
│  │ 🤖 R2 PRIME     🟢 9001  CPU 2% MEM 45MB       │ │
│  │  Asistente personal                              │ │
│  │  [Abrir Chat] [Logs] [⚙️] [⏹️ Stop]             │ │
│  ├─────────────────────────────────────────────────┤ │
│  │ ⚖️ Legal Assist  🟢 9002  CPU 1% MEM 32MB       │ │
│  │  Abogado laboral                                 │ │
│  │  [Abrir Chat] [Logs] [⚙️] [⏹️ Stop]             │ │
│  ├─────────────────────────────────────────────────┤ │
│  │ 🧾 BarOS         🔴 9003                         │ │
│  │  Gestión de bares                                │ │
│  │  [▶️ Start] [⚙️]                                 │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 3.3 Wizard de creación

```
┌──────────────────────────────────────────────────────┐
│  ✨ Crear Agente                    Paso 1 de 5      │
│                                                      │
│  Nombre del agente: [_____________________________] │
│  Descripción: [___________________________________] │
│                                                      │
│  📁 Ubicación de instalación:                       │
│  [C:\AgentOS\agents\              ] [📂 Examinar]  │
│                                                      │
│  [Siguiente →]                                       │
└──────────────────────────────────────────────────────┘

Paso 2: Personalidad (tono, tuteo, humor, prompt)
Paso 3: LLM (provider, modelo, temperatura, API key)
Paso 4: Tools + canales + permisos
Paso 5: Resumen y confirmación
```

### 3.4 Chat View (carga el chat del agente)

El frontend se conecta al proxy del Hub:
```
POST /api/v1/hub/proxy/{agent_name}/chat
```

O directamente al agente si se conoce el puerto:
```
POST http://localhost:{port}/api/v1/chat
```

### Checklist

- [ ] Proyecto React + Vite + TypeScript
- [ ] `Dashboard.tsx` — lista agentes con estado, CPU, RAM
- [ ] `CreateWizard.tsx` — 5 pasos: nombre+ubicación → personalidad → LLM → tools → resumen
- [ ] `AgentDetail.tsx` — ver config, acciones start/stop/restart/delete
- [ ] `ChatView.tsx` — burbujas, input, historial (conecta al proxy del Hub)
- [ ] `LogsView.tsx` — logs en vivo con tail
- [ ] `StatusBadge.tsx` — 🟢🔴🟡
- [ ] Conexiones a API del Hub
- [ ] Diseño responsive
- [ ] Estados: loading, empty, error

---

## Sprint 4 — Logs, Monitoreo, Auto-Restart (2 días)

### Objetivo
El Hub monitorea agentes, muestra logs en vivo, reinicia automáticamente si caen.

### Checklist

- [ ] Callbacks de log del agente al Hub
- [ ] Endpoint `GET /api/v1/hub/agents/{name}/logs?tail=N`
- [ ] WebSocket para logs en vivo (opcional, SSE como mínimo)
- [ ] Health checker con auto-restart funcional
- [ ] Stats por agente: tokens, tools, sesiones activas
- [ ] Endpoint `GET /api/v1/hub/stats` — resumen global
- [ ] Logs del Hub centralizados en `~/r2-hub/logs/hub.log`
- [ ] Probar: matar proceso de agente → se reinicia solo

---

## Sprint 5 — Primer Agente: R2 PRIME (1 día)

### Objetivo
El primer agente real funcionando. La configuración actual de R2 PRIME se convierte en agente.

### Config inicial

```yaml
# ~/r2-hub/agents/r2-prime/config.yaml
agent:
  name: "R2 PRIME"
  description: "Asistente personal de Xavier"
  port: 9001

personality:
  system_prompt: "Eres R2 PRIME, el asistente personal y arquitecto de software..."
  tone: "directo"
  humor: "sarcástico"

llm:
  provider: ollama
  model: qwen2.5:7b
  temperature: 0.7

tools:
  allow:
    - read_file
    - write_file
    - list_files
    - search_web
    - fetch_url
    - save_memory
    - get_memory
    - exec_command        # Nivel 3

security:
  level: 3
  sandbox:
    paths:
      - ~/Trantor/
      - ~/Documents/
      - ~/r2-hub/agents/r2-prime/data/

channels:
  web: true
  whatsapp:
    enabled: true
    phone: "+573192270876"

auto_restart: true
```

### Checklist

- [ ] Crear agente R2 PRIME desde el Hub
- [ ] Probar chat web con R2 PRIME
- [ ] Copiar tools dev (GitHub, exec) al agente
- [ ] Verificar sandbox: accede a ~/Trantor pero no a /etc
- [ ] Verificar que el agente arranca solo al iniciar Hub

---

## Sprint 6 — Canales: WhatsApp por Agente (2 días)

### Objetivo
Cada agente puede tener su propio canal de WhatsApp independiente.

### Cómo funciona

```text
Cada agente con WhatsApp tiene su propio sidecar:

~/r2-hub/agents/{name}/whatsapp/
├── session.json              ← Sesión de WhatsApp (QR escaneado)
├── sidecar.js                ← whatsapp-web.js sidecar
└── ...
```

El sidecar se comunica con el backend del agente por HTTP local.

```text
WhatsApp → Sidecar.js → POST /api/v1/chat del agente → Respuesta → WhatsApp
```

Múltiples agentes pueden tener WhatsApp activo, cada uno con su propio número.

### Checklist

- [ ] Sidecar de WhatsApp como template (copia por agente)
- [ ] Cada sidecar con su propia sesión (session.json independiente)
- [ ] Canal configurable por agente (`config.yaml → channels.whatsapp`)
- [ ] El Hub expone QR generation para cada agente con WhatsApp
- [ ] Reconexión automática por agente
- [ ] Probar: 2 agentes con WhatsApp funcionando simultáneamente

---

## Sprint 7 — Empaquetado + Instalador (2 días)

### Objetivo
Cualquier persona puede instalar R2 Hub en 5 minutos.

### Checklist

- [ ] `install.sh` — macOS/Linux
- [ ] `install.bat` — Windows
- [ ] Script que:
  - [ ] Verifica Python 3.11+
  - [ ] Crea el virtualenv
  - [ ] Instala dependencias
  - [ ] Crea ~/r2-hub/ + estructura base
  - [ ] Copia templates
  - [ ] Crea agente por defecto (R2 PRIME)
  - [ ] Lanza Hub
- [ ] `uninstall.sh` — limpia todo (preguntando)
- [ ] Sistema de backups: `r2-hub export {agent}` → .r2agent tar.gz

---

## Sprint 8 — Endurecimiento de seguridad (2 días) 🔴

### Objetivo
Los templates copian `security/` de la v1 tal cual (líneas 106-108), heredando bugs reales. Antes de lanzar hay que cerrarlos. Meta: **seguridad pragmática, no cárcel** — configurable por agente, con confirmación solo en lo peligroso.

### Deuda heredada de la v1 (verificada 17 Jul 2026)
- `exec_command` tiene whitelist que se salta trivialmente: `python -c`, `node -e`, `find -exec`, `npx *` → RCE. La validación de args deja pasar cualquier flag que empiece con `-`.
- `exec_command` ignora el sandbox: `cat`/`cp`/`mv` leen/escriben fuera de las carpetas permitidas.
- `requires_confirmation` está declarado en las tools pero el orquestador nunca lo aplica.
- Nivel 3 fijo + sin auth + `host=0.0.0.0` + CORS `*` → cualquiera en la LAN tiene acceso autónomo.

### Checklist
- [ ] Rehacer validación de `exec_command` (o quitar `python -c`/`node -e`/`find`/`npx` de la whitelist)
- [ ] Aplicar sandbox también a `exec_command` (no solo a file_tools)
- [ ] Implementar el gate de `requires_confirmation` en el orquestador + flujo two-step en `/chat`
- [ ] Permisos **por agente** (definidos en el wizard) en vez de niveles rígidos globales
- [ ] Auth por agente + bind `127.0.0.1` + CORS restringido
- [ ] Tests de seguridad: `rm -rf`/`sudo` fallan, intento de RCE falla, escape de sandbox falla, sin auth se rechaza
- [ ] Verificar aislamiento: un agente no puede tocar la carpeta de otro

---

## 🔄 Roadmap Post-MVP

```text
v2.1 — Comunicación entre agentes
  → Hub como router de mensajes entre agentes
  → "R2 PRIME, pídele a Legal que revise este contrato"

v2.2 — Pool compartido de LLMs
  → Los agentes no cargan su propio modelo
  → El Hub asigna modelos según demanda
  → Ahorra RAM: 1 modelo en RAM en vez de N

v2.3 — Plugin Store
  → Tools descargables desde GitHub
  → Instalar tools de terceros por agente

v2.4 — Modo multiusuario
  → Cada usuario ve solo sus agentes
  → Login, auth, roles
```

---

## 📊 Esfuerzo estimado

| Sprint | Días | Entregable | ¿Qué tan crítico? |
|--------|------|-----------|-------------------|
| 1 | 3 | Hub gestiona procesos | 🔴 MVP |
| 2 | 3 | Engine funcional | 🔴 MVP |
| 3 | 4 | Frontend completo | 🟡 Puede empezar con API |
| 4 | 2 | Logs + monitoreo | 🟡 |
| 5 | 1 | R2 PRIME | 🔴 MVP |
| 6 | 2 | WhatsApp | 🟡 |
| 7 | 2 | Instalador | 🔴 Lanzamiento |
| 8 | 2 | Endurecimiento de seguridad | 🔴 Pre-lanzamiento |
| **9** | **4** | **Exportación de agentes** | **🔴 Lanzamiento** |

**MVP mínimo** (Sprints 1+2+5): ~7 días → Hub + 1 agente funcional por web
**Lanzamiento** (Sprints 1-9): ~23 días

> ⚠️ **Sprint 8 no es opcional antes de sacar el Hub de localhost o vendérselo a un cliente.** Puede adelantarse si un agente va a exponerse a la red antes del empaquetado.

---

## Sprint 9 — Exportación de Agentes (4 días)

### Objetivo
El Hub puede exportar cualquier agente como paquete `.tar.gz` que se instala
en cualquier máquina y corre como app nativa independiente, sin dependencias.

**Archivo de referencia:** `EXPORT.md` (concepto completo).

### 9.1 Exportación

En el Hub → click derecho en un agente → [📦 Exportar]
→ Se genera: `agente-pos-v1.0.tar.gz`

Contenido del paquete:

```text
📦 agente-pos-v1.0.tar.gz
├── install.sh
├── uninstall.sh
├── app/                    ← App nativa Tauri (R2 Agent.app)
│   └── R2 Agent.app       ← .dmg / .exe / .AppImage
├── engine/
│   └── r2-engine          ← Rust compilado (~8 MB)
├── agent/
│   ├── specialty.json     ← Personalidad + tools
│   ├── knowledge/         ← Docs + RAG index
│   ├── memory/            ← Sesiones + aprendizaje
│   └── audit/             ← Historial de acciones
└── config.yaml            ← Default (editable)
```

**La exportación incluye TODO:** personalidad, conocimiento, memoria completa
(sesiones, feedback, aprendizaje), historial de acciones y app nativa.

### 9.2 Importación e instalación

```bash
$ r2 import agente-pos-v1.0.tar.gz
✓ Extrayendo...
✓ Engine instalado
✓ App creada en el menú
✓ Icono 🤖 en la bandeja del sistema
```

**Sin dependencias:**
- ❌ Python / Node / Docker / nada
- ✅ Solo necesita Ollama (o API key)
- ✅ Sin navegador — app nativa
- ✅ Sin terminal — icono en bandeja

### 9.3 Actualización y rollback

```bash
$ r2 update agente-pos-v2.0.tar.gz
✓ Memoria preservada (no pierde lo aprendido)
✓ Config local preservada

$ r2 rollback
✓ Vuelto a v1.0
```

### 9.4 Caso de uso: POS Expert

```text
Hub → Creas agente POS Expert con tools del POS
    → [Exportar] → agente-pos-v1.0.tar.gz
    → Lo copias a 5 bares distintos
    → Cada bar: $ r2 import → 🤖 en bandeja
    → El cajero habla con el agente sin abrir navegador
    → Mejoras → exportas v2.0 → r2 update en todos
```

### Checklist

- [ ] `r2 export` en Hub → genera `.tar.gz` completa
- [ ] `r2 import <package>` → extrae + configura + deja corriendo
- [ ] `r2 update <package>` → actualiza sin perder memoria/config
- [ ] `r2 rollback` → vuelve a versión anterior
- [ ] App nativa Tauri empaquetada dentro del `.tar.gz`
- [ ] Instalación sin dependencias (solo Ollama)
- [ ] Cross-platform: .dmg / .exe / .AppImage
