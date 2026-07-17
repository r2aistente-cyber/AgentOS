# 🤖 R2 Hub — Plataforma de Agentes Independientes

> **Versión:** 2.0
> **Fecha:** 2026-07-17
> **Estado:** Reinicio completo del concepto

---

## 🎯 El Concepto

R2 Hub no es un agente. Es una **plataforma para crear y gestionar agentes**.

Cada agente es una entidad independiente con su propio espacio en disco, su propia memoria, su propio backend. El Hub es el "sistema operativo" que los crea, los lanza, los monitorea y los detiene.

```
┌───────────────────────────────────────────────────────────┐
│                     AgentOS (la ventana)                  │
│  Dashboard │ Crear Agente │ Gestionar │ Logs │ Config      │
└──────────────────────┬────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  🤖 Agente A │ │  🤖 Agente B │ │  🤖 Agente C │
│              │ │              │ │              │
│  D:\Agentes/ │ │  C:\Users/   │ │  E:\Legal/   │
│  R2 PRIME/   │ │  .../BarOS/  │ │  .../        │
│  ────────    │ │  ────────    │ │  ────────    │
│  config.yaml │ │  config.yaml │ │  config.yaml │
│  memory.db   │ │  memory.db   │ │  memory.db   │
│  data/       │ │  data/       │ │  data/       │
│  tools/      │ │  tools/      │ │  tools/      │
│  port 9001   │ │  port 9002   │ │  port 9003   │
│  status: 🟢  │ │  status: 🟢  │ │  status: 🔴  │
└──────────────┘ └──────────────┘ └──────────────┘

// Cada agente en la ubicación que el usuario eligió al crearlo.
// El Hub NO los centraliza en una carpeta — solo los registra.
```

---

## 🏗️ Arquitectura General

### El Hub (Puerto 8234)

El Hub NO conversa con nadie. Es solo el administrador.

| Función | Descripción |
|---------|-------------|
| **Dashboard** | Pantalla principal con todos los agentes, su estado (online/offline), recursos (CPU, RAM, disco) |
| **Crear Agente** | Wizard para crear un agente nuevo: nombre, personalidad, modelo LLM, tools, permisos |
| **Gestionar** | Start / Stop / Restart / Delete agentes |
| **Logs** | Logs en tiempo real de cada agente |
| **Config** | Configuración global del Hub (puertos, ruta base, etc.) |

### El Manager de Procesos

El Hub lanza cada agente como un **subproceso independiente**. Cada uno es un proceso FastAPI separado.

```python
# El Hub controla los procesos de los agentes
class AgentManager:
    agents: dict[str, AgentProcess]
    
    def create(name, config) -> AgentProcess:
        # 1. Crear directorio: ~/r2-hub/agents/{name}/
        # 2. Generar config.yaml
        # 3. Copiar plantilla base del backend
        # 4. Inicializar SQLite memory.db
        # 5. Asignar puerto único (9000+)
        # 6. Devolver proceso

    def start(name) -> Process:
        # Lanzar: uvicorn agent_main:app --port {port}
        # Registrar en el health checker
    
    def stop(name):
        # Enviar SIGTERM al proceso
    
    def status(name) -> str:
        # "online" | "offline" | "starting" | "error"
```

### El Health Checker

El Hub monitorea que cada agente esté vivo. Si un agente crashea, lo reinicia automáticamente (opcional).

```python
class HealthChecker:
    def check(self, agent) -> bool:
        # GET /api/v1/health del agente
        # Si no responde en 5s, marcar como offline
```

---

## 🤖 Cada Agente

### Estructura en disco (ejemplo con 3 agentes en ubicaciones diferentes)

```
C:\AgentOS\                        ← Instalación del programa
├── AgentOS.exe                    ← La app que abre Javier
├── hub-engine.exe                 ← Backend del Hub (servicio/sidecar)
├── config.yaml                    ← Config del Hub
└── templates/                     ← Plantillas para nuevos agentes
    ├── agent_main.py
    ├── default_config.yaml
    └── ...

D:\Agentes\                         ← Primer agente, Javier eligió D:\
└── R2 PRIME\
    ├── config.yaml
    ├── agent_main.py
    ├── memory.db
    ├── data\
    └── logs\

C:\Users\Xavier\Documents\Bufete\   ← Segundo agente, en Documentos
└── Abogado Laboral\
    ├── config.yaml
    ├── agent_main.py
    ├── memory.db
    ├── data\
    │   └── demandas\
    └── logs\

E:\Marketing\                       ← Tercer agente, en otro disco
└── Marketing Bot\
    ├── config.yaml
    ├── agent_main.py
    ├── memory.db
    ├── data\
    └── logs\
```

**Cada agente en la ubicación que el usuario eligió.** No hay directorio central de agentes. El Hub sabe dónde está cada uno porque lo guarda en su registro.

### Independencia total

Cada agente:

| Característica | Descripción |
|----------------|-------------|
| 🗄️ **Memoria propia** | SQLite `memory.db` — no comparte sesiones con nadie |
| 📁 **Archivos aislados** | `data/` — solo el agente accede a sus archivos |
| ⚙️ **Config propia** | `config.yaml` — modelo LLM, tools, personalidad, nivel de acceso |
| 🔌 **Proceso separado** | Su propio proceso Python en su propio puerto |
| 🧠 **LLM propio** | Puede usar su propio modelo (qwen2.5:7b, deepseek, gpt-4, etc.) |
| 🛠️ **Tools propias** | Puede tener herramientas que otros agentes no tienen |
| 🌐 **Interfaz propia** | Cada agente tiene su propia URL de chat |
| 💬 **Canales propios** | Puede tener WhatsApp, Telegram, web — o no tener ninguno |

### Config de un agente (config.yaml)

```yaml
# D:\AgentOS\agents\R2 PRIME\config.yaml
agent:
  name: "R2 PRIME"
  description: "Asistente personal de Xavier"
  install_path: "D:\AgentOS\agents\R2 PRIME"
  port: 9001
  status: online

personality:
  tone: "directo"
  humor: "sarcástico"
  empathy: "leal"
  system_prompt: "Eres R2 PRIME, el asistente personal de Xavier..."

llm:
  provider: ollama           # ollama | openai | anthropic | google | custom
  api_key: ""                # Solo para proveedores externos (OpenAI, etc.)
  model: qwen2.5:7b          # o gpt-4o, claude-sonnet-4, gemini-2.0-flash, etc.
  temperature: 0.7
  host: http://localhost:11434  # Ollama o endpoint custom

tools:
  allow:
    - read_file
    - write_file
    - list_files
    - search_web
    - fetch_url
    - save_memory
    - get_memory
    - exec_command     # Solo si level >= 3
    - read_image       # Analizar imágenes con visión
    - read_document    # Leer PDFs, DOCX, TXT
    - read_audio       # Transcripción de audio
  deny: []

security:
  level: 3
  sandbox:
    paths:
      - D:\AgentOS\agents\R2 PRIME\data\

files:
  max_upload_size_mb: 50
  allowed_extensions:
    - .txt
    - .pdf
    - .docx
    - .xlsx
    - .jpg
    - .png
    - .webp
    - .mp3
    - .wav
    - .csv
    - .json
    - .py
    - .js
    - .html

channels:
  web: true
  whatsapp:
    enabled: true
    phone: "+573192270876"
  telegram:
    enabled: false

auto_restart: true
```

### Adjuntar archivos al agente

Cuando hablas con un agente, puedes arrastrar o adjuntar archivos. El agente los recibe, los guarda en su `data/`, los procesa según el tipo y responde basado en su contenido.

| Tipo de archivo | Cómo lo procesa el agente |
|----------------|---------------------------|
| 📄 **PDF / DOCX / TXT** | Extrae el texto y lo usa como contexto para responder |
| 🖼️ **JPG / PNG / WebP** | Lo analiza con visión del LLM (si el modelo lo soporta) |
| 🎵 **MP3 / WAV** | Lo transcribe a texto (whisper local o API) |
| 📊 **CSV / XLSX** | Lee los datos y responde preguntas sobre ellos |
| 📝 **JSON / XML** | Lo parsea y lo usa como contexto |
| 💻 **Código (.py, .js, etc.)** | Lee el código y lo analiza |

**Los archivos se guardan en la carpeta `data/` del agente.** Quedan disponibles para futuras conversaciones a menos que se eliminen explícitamente.

El sandbox del agente restringe qué archivos puede leer. Si el usuario adjunta un archivo, el agente lo recibe en su `data/attachments/`. Si el usuario pregunta por un archivo que ya está en `data/`, el agente lo puede leer directamente.

---

## 🖥️ El Hub UI (Frontend React)

### Dashboard

```
┌──────────────────────────────────────────────────────┐
│  R2 Hub ··· ☰                                       │
│                                                      │
│  🤖 R2 PRIME     🟢 Online  ···  9001  ████░░ 45%  │
│     Asistente personal · Xavier                      │
│                                                      │
│  ⚖️ Legal Assist   🟢 Online  ···  9002  ██░░░░ 20% │
│     Abogado laboral · Bufete Pérez                   │
│                                                      │
│  🧾 BarOS          🔴 Offline ···  9003              │
│     Gestión de bares                                 │
│                                                      │
│  [ + Crear Agente ]                                  │
└──────────────────────────────────────────────────────┘
```

### Crear Agente (Wizard)

Paso 1 — **Nombre y ubicación**
```
┌──────────────────────────────────────────────────────┐
│  ✨ Crear Agente                   Paso 1 de 5       │
│                                                      │
│  Nombre: [Legal Assistant              ]             │
│  Descripción: [Abogado laboral para el bufete]       │
│                                                      │
│  📁 Ubicación de instalación:                        │
│  [C:\AgentOS\agents\Legal Assistant\]  [📂 Buscar] │
│                                                      │
│  [← Atrás]     [Siguiente →]                         │
└──────────────────────────────────────────────────────┘
```

Paso 2 — **Personalidad**
```
┌──────────────────────────────────────────────────────┐
│  ✨ Crear Agente                   Paso 2 de 5       │
│                                                      │
│  Personalidad:                                       │
│  ○ Directo     ○ Formal    ● Profesional             │
│  ○ Divertido   ○ Cálido                              │
│                                                      │
│  ○ Tutea  ● Usted                                    │
│                                                      │
│  [← Atrás]     [Siguiente →]                         │
└──────────────────────────────────────────────────────┘
```

### Logs en vivo

```
┌──────────────────────────────────────────────────────┐
│  📋 R2 PRIME — Logs en vivo                         │
│                                                      │
│  [17:30:22] ✅ Tool: search_web → "jurisprudencia   │
│             despido injusto"                         │
│  [17:30:25] 🤖 Respuesta generada (342 tokens)      │
│  [17:30:26] 📤 Enviado a WhatsApp                    │
│  [17:30:28] 💾 Memoria guardada: "cliente" →        │
│             "Juan Pérez"                             │
│                                                      │
│  [━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━]          │
│  Todos los sistemas OK                               │
└──────────────────────────────────────────────────────┘
```

---

## 🔌 Comunicación Hub ↔ Agentes

El Hub se comunica con los agentes a través de **HTTP**. El Hub sabe el puerto de cada agente.

```python
# Hub → Agente
class HubAgentClient:
    def chat(self, agent_name, message) -> str:
        port = self.registry[agent_name].port
        r = requests.post(
            f"http://localhost:{port}/api/v1/chat",
            json={"message": message}
        )
        return r.json()["reply"]
    
    def health(self, agent_name) -> bool:
        port = self.registry[agent_name].port
        try:
            r = requests.get(f"http://localhost:{port}/api/v1/health", timeout=3)
            return r.status_code == 200
        except:
            return False
```

Los agentes **no se comunican entre sí**. Están aislados por diseño. Si se necesita comunicación entre agentes, se hace a través del Hub como intermediario (futuro).

---

## 🛠️ Engine Template (base para todo agente)

Cada agente se crea a partir de una **plantilla base** (`templates/agent_main.py`) que incluye:

```python
# templates/agent_main.py — Template para crear agentes
import yaml
from fastapi import FastAPI
from llm.adapter import LLMAdapter
from tools.orchestrator import ToolOrchestrator
from memory.db import Database
from security.permissions import PermissionEnforcer

# Cargar config del agente
config = yaml.safe_load(open("config.yaml"))

# Inicializar componentes
app = FastAPI(title=config["agent"]["name"])
llm = LLMAdapter(config["llm"])
tools = ToolOrchestrator(config["tools"])
memory = Database("memory.db")
security = PermissionEnforcer(config["security"])

@app.post("/api/v1/chat")
async def chat(session_id: str, message: str):
    # 1. Cargar sesión
    session = memory.get_session(session_id)
    # 2. Llamar LLM con tools
    response = await llm.chat(session.messages, message, tools.list())
    # 3. Ejecutar tools si aplica
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = tools.execute(tool_call)
            session.add_result(result)
    # 4. Guardar y responder
    session.save()
    return {"reply": response.content}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "uptime": ...}
```

Esta plantilla se copia al directorio del nuevo agente. Se puede personalizar después (tools, canales, etc.).

---

## 📊 Comparativa: Antes vs Ahora

| Aspecto | Antes (v1) | Ahora (v2 Hub) |
|---------|-----------|----------------|
| Arquitectura | 1 backend + especialidades JSON | Hub + N agentes independientes |
| Cada agente | Solo cambia el JSON | Entidad completa con disco propio |
| Aislamiento | Comparten backend y BD | Cada uno su proceso, su BD, sus archivos |
| Escalabilidad | Un cuello de botella | Cada agente escala independiente |
| Si un agente falla | Tira todo | Solo ese agente se cae |
| Crear agente | Copiar JSON | Wizard con creación de directorio |
| Personalización | Limitada a JSON | Total: tools, canales, modelo, permisos |
| Monitoreo | No hay | Dashboard en vivo con logs |

---

## 🎯 Casos de Uso

### Para Xavier (personal)

```
  🤖 R2 PRIME — Asistente personal
  → Puerto 9001
  → LLM: ollama / qwen2.5:7b
  → Canales: WhatsApp, Web
  → Tools: Todo (Nivel 3)
  → Acceso a: ~/Trantor, ~/Documents

  ⚖️ Legal Assistant — Trabajo
  → Puerto 9002
  → LLM: ollama / qwen2.5:7b (temperatura baja)
  → Canales: Web
  → Tools: read/write documentos, búsqueda legal
  → Acceso a: ~/r2-hub/agents/legal-assistant/data/
```

### Para clientes (Enterprise)

```
  🧾 BarOS — Dueño de bar
  → Puerto 9003
  → LLM: ollama / qwen2.5:1.5b (rápido, barato)
  → Canales: WhatsApp
  → Tools: consultar_ventas, controlar_stock
  → Acceso a: solo su data/
  → Nivel: 1 (solo lectura + escritura controlada)

  📢 Marketing Bot
  → Puerto 9004
  → LLM: openai / gpt-4o (API key propia)
  → Canales: Web
  → Tools: generar_post, programar_publicación
```

---

## 🔮 Futuro

### Comunicación entre agentes (Post-MVP)

El Hub podría permitir que agentes colaboren:

```
Usuario: "Legal, necesito una demanda. Pídele a R2 PRIME 
         los datos del cliente."

Legal → Hub → R2 PRIME: "Dame los datos de Juan Pérez"
R2 PRIME → Hub → Legal: "Aquí están: CC 12345, dirección..."
```

### Pool de LLMs compartido

Los agentes podrían compartir un pool de modelos de Ollama para no cargar el mismo modelo N veces. El Hub asigna modelos disponibles a los agentes que los necesiten. Para proveedores externos (OpenAI, Anthropic), el Hub puede gestionar keys globales que los agentes heredan.

### Exportar / Importar agentes

Un agente completo (config + data + memory) se empaqueta como `.r2agent` y se puede mover a otra PC.

---

## 💡 Filosofía

R2 Hub no es "un agente que hace todo". Es **tu fábrica de agentes**.

Cada agente es especializado, aislado, y manejable. No mezclas la conversación personal de Xavier con los documentos legales del bufete. No arriesgas que un error en BarOS borre datos de Marketing.

El Hub es el taller. Tú decides qué agentes construir.
