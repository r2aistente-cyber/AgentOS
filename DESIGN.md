# 🧠 R2 Autonomous — Tool Orchestrator Spec

> **Versión:** 1.0  
> **Autor:** R2 PRIME (Concepto)  
> **Propósito:** Especificación técnica para que Trantor implemente el núcleo del agente autónomo.  
> **Estado:** Borrador para revisión

---

## 1. Arquitectura General

```
                    ┌──────────────────────────┐
                    │      Usuario (Web)        │
                    │      o WhatsApp           │
                    └────────────┬─────────────┘
                                 │ POST /api/chat
                                 ▼
                    ┌──────────────────────────┐
                    │     FastAPI Server        │
                    │   (backend/main.py)       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │     Session Manager       │
                    │   - Crea/reanuda sesión   │
                    │   - Carga historial       │
                    │   - Carga memoria larga   │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │     LLM Router            │
                    │   - Envía prompt a Ollama │
                    │   - Procesa respuesta     │
                    │   - Detecta tool calls    │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │     Tool Orchestrator     │
                    │   - Recibe tool call      │
                    │   - Valida permisos       │
                    │   - Ejecuta herramienta   │
                    │   - Devuelve resultado    │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │  File System  │   │   SQLite DB   │   │    Web       │
    │  (sandbox)    │   │   (memoria)   │   │  (scrape)    │
    └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 2. API Endpoints (FastAPI)

### 2.1 Chat

```yaml
POST /api/v1/chat
  URL: http://localhost:8234/api/v1/chat
  Body:
    session_id: str (opcional, si es nueva omitir)
    message: str
    user_id: str
    specialty_id: str (opcional, default "default")
  
  Response:
    session_id: str
    reply: str
    tools_used: list[str]
    tokens_used: int

GET /api/v1/chat/{session_id}
  Returns historial completo de la sesión

DELETE /api/v1/chat/{session_id}
  Limpia historial de la sesión
```

### 2.2 Sesiones

```yaml
GET /api/v1/sessions?user_id=xxx
  Lista sesiones activas del usuario

POST /api/v1/sessions/new
  Body: { user_id, specialty_id }
  Response: { session_id }

POST /api/v1/sessions/{id}/archive
  Archiva la sesión (no se borra)
```

### 2.3 Especialidades

```yaml
GET /api/v1/specialties
  Lista especialidades instaladas

GET /api/v1/specialties/{id}
  Detalle de una especialidad

POST /api/v1/specialties/install
  Body: (multipart) JSON + archivos de conocimiento
  Instala nueva especialidad
```

### 2.4 Archivos

```yaml
POST /api/v1/upload
  Body: multipart/file
  Response: { file_id, filename, size, path }

GET /api/v1/files/{file_id}
  Descarga archivo

DELETE /api/v1/files/{file_id}
  Elimina archivo
```

### 2.5 Admin / Seguridad

```yaml
GET /api/v1/admin/users
  Lista usuarios

POST /api/v1/admin/users
  Crea/actualiza usuario

GET /api/v1/admin/audit?user_id=xxx
  Log de auditoría filtrado

POST /api/v1/admin/permissions
  Body: { user_id, level: 0|1|2|3 }
```

---

## 3. Tool System

### 3.1 Definición de herramienta

Cada herramienta es una función registrada con metadata:

```python
@dataclass
class Tool:
    name: str                    # Identificador único
    description: str             # Para el LLM
    category: str                # file | db | web | comms | system
    min_level: int               # Nivel mínimo de permiso
    parameters: list[Param]      # Parámetros que acepta
    requires_confirmation: bool  # ¿Preguntar al usuario?
    timeout_seconds: int         # Timeout máximo

@dataclass
class Param:
    name: str
    type: str                    # string | integer | boolean | file
    description: str
    required: bool
    enum: list[str] | None       # Valores permitidos
```

### 3.2 Herramientas base (core)

```python
tools_registry = {
    # Archivos
    "read_file": Tool(
        name="read_file",
        description="Lee el contenido de un archivo. Ruta relativa al sandbox.",
        category="file",
        min_level=1,
        parameters=[Param("path", "string", "Ruta del archivo", True)],
        requires_confirmation=False,
    ),
    "write_file": Tool(
        name="write_file",
        description="Escribe contenido en un archivo. Si existe, lo sobrescribe.",
        category="file",
        min_level=2,
        parameters=[
            Param("path", "string", "Ruta del archivo", True),
            Param("content", "string", "Contenido a escribir", True),
        ],
        requires_confirmation=True,
    ),
    "list_files": Tool(
        name="list_files",
        description="Lista archivos en un directorio del sandbox.",
        category="file",
        min_level=1,
        parameters=[Param("path", "string", "Ruta del directorio", False)],
        requires_confirmation=False,
    ),
    
    # Base de datos
    "query_db": Tool(
        name="query_db",
        description="Ejecuta una consulta SQL de solo lectura en la BD.",
        category="db",
        min_level=1,
        parameters=[Param("query", "string", "Consulta SQL SELECT", True)],
        requires_confirmation=False,
    ),
    "save_memory": Tool(
        name="save_memory",
        description="Guarda un dato en la memoria a largo plazo del usuario.",
        category="db",
        min_level=1,
        parameters=[
            Param("key", "string", "Clave del dato", True),
            Param("value", "string", "Valor del dato", True),
        ],
        requires_confirmation=False,
    ),
    "get_memory": Tool(
        name="get_memory",
        description="Recupera un dato de la memoria a largo plazo.",
        category="db",
        min_level=1,
        parameters=[Param("key", "string", "Clave a buscar", True)],
        requires_confirmation=False,
    ),
    
    # Web / Internet
    "search_web": Tool(
        name="search_web",
        description="Busca información en internet.",
        category="web",
        min_level=1,
        parameters=[Param("query", "string", "Términos de búsqueda", True)],
        requires_confirmation=False,
    ),
    "fetch_url": Tool(
        name="fetch_url",
        description="Obtiene el contenido de una URL.",
        category="web",
        min_level=1,
        parameters=[Param("url", "string", "URL a obtener", True)],
        requires_confirmation=False,
    ),
    
    # WhatsApp
    "send_whatsapp": Tool(
        name="send_whatsapp",
        description="Envía un mensaje de WhatsApp.",
        category="comms",
        min_level=3,
        parameters=[
            Param("to", "string", "Número destino (+57...)", True),
            Param("message", "string", "Mensaje a enviar", True),
        ],
        requires_confirmation=True,
    ),
}
```

### 3.3 Cómo el LLM llama herramientas — NATIVO (Ollama API)

Ollama soporta `tools` en su API de chat. El modelo sabe qué herramientas
disponibles tiene y las llama con la estructura correcta.

**El LLM no produce JSON manual.** El API de Ollama maneja todo.

#### Llamada a Ollama con tools

```python
# No parseamos JSON. Ollama lo hace.

response = ollama.chat(
    model="qwen2.5:7b",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Lee el contenido de un archivo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Ruta del archivo"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Busca información en internet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Términos de búsqueda"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
)

# La respuesta ya viene estructurada:
if response["message"].get("tool_calls"):
    for tool_call in response["message"]["tool_calls"]:
        name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        result = orchestrator.execute(name, args)
        
        # Enviar resultado de vuelta al modelo
        messages.append({
            "role": "tool",
            "content": str(result),
            "name": name
        })
    
    # El modelo responde basado en el resultado
    final = ollama.chat(model="qwen2.5:7b", messages=messages)
```

#### Estructura de herramientas en OpenAPI Schema

```python
def get_tools_for_level(level: int) -> list[dict]:
    """Convierte las Tools del registry al formato que Ollama entiende."""
    tools = []
    for tool in registry.list():
        if level < tool.min_level:
            continue
        
        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p.name: {
                            "type": p.type,
                            "description": p.description,
                        }
                        for p in tool.parameters
                    },
                    "required": [p.name for p in tool.parameters if p.required],
                }
            }
        })
    return tools
```

#### El system prompt ya no necesita el JSON manual

```text
## Capacidades
Puedes usar herramientas para:
- Leer y escribir archivos
- Buscar en internet
- Consultar la base de datos
- Enviar WhatsApp

Cuando necesites una herramienta, el sistema la manejará automáticamente.
Solo di qué necesitas en lenguaje natural.

El sistema te pasará el resultado y tú interpretas lo que significa.
```

El LLM se enfoca en pensar y razonar. La estructura de la llamada la maneja el API.

---

## 4. LLM Integration

### 4.1 Configuración

```python
# config.py
LLM_CONFIG = {
    "default": {
        "model": "qwen2.5:7b",
        "host": "http://localhost:11434",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_length": 8192,
    },
    "legal": {
        "model": "qwen2.5:7b",
        "temperature": 0.3,   # Más preciso, menos creativo
        "max_tokens": 8192,
    },
    "baros": {
        "model": "qwen2.5:1.5b",
        "temperature": 0.8,   # Más conversacional
        "max_tokens": 2048,
    },
}
```

### 4.2 Chat handler flow (con native tool calling)

```python
def get_tools_for_specialty(specialty: Speciality, user_level: int) -> list:
    """Convierte herramientas del registry al formato de Ollama."""
    return [
        tool.to_ollama_format()
        for tool in registry.list()
        if user_level >= tool.min_level
        and tool.name not in specialty.config.get("deny_tools", [])
    ]


async def chat(session_id, message, user_id, specialty_id):
    # 1. Cargar sesión
    session = SessionManager.get(session_id, user_id)
    user = AuthManager.get_user(user_id)
    specialty = SpecialtyManager.get(specialty_id or user.default_specialty)
    
    # 2. Construir mensajes
    messages = [
        {"role": "system", "content": specialty.system_prompt},
        *session.get_recent_messages(limit=20),
        {"role": "user", "content": message},
    ]
    
    # 3. Obtener herramientas disponibles para este usuario+especialidad
    tools = get_tools_for_specialty(specialty, user.level)
    
    # 4. Llamar a Ollama con tools nativo
    response = await ollama.chat(
        model=specialty.model,
        messages=messages,
        tools=tools,  # ← NATIVO, no parseamos nada
    )
    
    msg = response["message"]
    
    # 5. ¿El modelo pidió usar una herramienta?
    if msg.get("tool_calls"):
        for tool_call in msg["tool_calls"]:
            name = tool_call["function"]["name"]
            args = tool_call["function"]["arguments"]
            
            # Ejecutar herramienta
            result = orchestrator.execute(name, args, user)
            
            # Enviar resultado al modelo
            messages.append({
                "role": "tool",
                "content": json.dumps(result),
                "name": name,
            })
        
        # 6. El modelo produce respuesta final con el resultado
        response = await ollama.chat(
            model=specialty.model,
            messages=messages,
            tools=tools,
        )
        content = response["message"]["content"]
    else:
        # Sin tool call — respuesta directa
        content = msg["content"]
    
    # 7. Guardar en BD
    session.add_message("user", message)
    session.add_message("assistant", content)
    
    return {
        "session_id": session.id,
        "reply": content,
        "tools_used": [
            tc["function"]["name"]
            for tc in msg.get("tool_calls", [])
        ]
    }
```

---

## 5. Database Schema (SQLite)

```sql
-- Sesiones de conversación
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,      -- UUID
    user_id     TEXT NOT NULL,
    specialty_id TEXT DEFAULT 'default',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      BOOLEAN DEFAULT 1,
    archived    BOOLEAN DEFAULT 0
);

-- Mensajes individuales
CREATE TABLE messages (
    id          TEXT PRIMARY KEY,      -- UUID
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,         -- 'user' | 'assistant' | 'system' | 'tool'
    content     TEXT NOT NULL,
    tools_used  TEXT,                  -- JSON list
    tokens      INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Memoria a largo plazo (clave-valor por usuario)
CREATE TABLE long_term_memory (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    category    TEXT DEFAULT 'general', -- 'preference' | 'fact' | 'context'
    confidence  REAL DEFAULT 1.0,      -- 0.0 a 1.0
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);

-- Usuarios del sistema
CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT DEFAULT 'user',    -- 'admin' | 'user' | 'readonly'
    permission_level INTEGER DEFAULT 1, -- 0-3
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      BOOLEAN DEFAULT 1
);

-- Especialidades instaladas
CREATE TABLE specialties (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    version     TEXT DEFAULT '1.0',
    config      TEXT NOT NULL,          -- JSON completo de la especialidad
    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    active      BOOLEAN DEFAULT 1
);

-- Auditoría de herramientas
CREATE TABLE audit_log (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    session_id  TEXT,
    tool_name   TEXT NOT NULL,
    params      TEXT,                   -- JSON
    result      TEXT,                   -- JSON
    success     BOOLEAN,
    duration_ms INTEGER,
    ip_address  TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Seguridad — Implementación

### 6.1 Sandbox de archivos

```python
import os
from pathlib import Path

class Sandbox:
    """Restringe acceso del agente a carpetas permitidas."""
    
    ALLOWED_DIRS = [
        Path("/home/abogado/casos"),
        Path("/home/abogado/plantillas"),
        Path("/tmp/r2-temp"),
    ]
    
    @classmethod
    def resolve_path(cls, rel_path: str) -> Path:
        """Resuelve una ruta relativa dentro del sandbox.
        
        Lanza PermissionError si intenta salir del sandbox.
        """
        # Intentar en cada directorio permitido
        for base in cls.ALLOWED_DIRS:
            full = (base / rel_path).resolve()
            # Verificar que está dentro del directorio permitido
            if str(full).startswith(str(base)):
                if full.exists() or full.parent.exists():
                    return full
        
        raise PermissionError(f"Acceso denegado: {rel_path}")
```

### 6.2 Permission levels enforcement

```python
class PermissionEnforcer:
    """Valida cada acción contra el nivel de permiso del usuario."""
    
    LEVEL_0 = 0  # Solo conversación
    LEVEL_1 = 1  # Lectura
    LEVEL_2 = 2  # Lectura + escritura controlada
    LEVEL_3 = 3  # Acción autónoma
    
    REQUIRES_CONFIRMATION = {
        "write_file": LEVEL_2,
        "delete_file": LEVEL_2,
        "send_whatsapp": LEVEL_3,
        "execute_command": LEVEL_3,
        "modify_db": LEVEL_2,
    }
    
    @classmethod
    def check(cls, tool_name: str, user_level: int) -> bool:
        return user_level >= cls.REQUIRES_CONFIRMATION.get(tool_name, LEVEL_0)
```

---

## 7. Estructura de Archivos (backend)

```
r2-autonomous/
├── backend/
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Configuración global
│   ├── requirements.txt          # Dependencias Python
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py             # Conexión a Ollama
│   │   ├── prompts.py            # Construcción de prompts
│   │   └── parser.py             # Parseo de tool calls desde respuesta
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── orchestrator.py       # ToolOrchestrator class
│   │   ├── registry.py           # Registro de herramientas
│   │   ├── file_tools.py         # read/write/list files
│   │   ├── db_tools.py           # query/save/get memory
│   │   ├── web_tools.py          # search/fetch web
│   │   └── comms_tools.py        # WhatsApp
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── sandbox.py            # Restricción de archivos
│   │   ├── permissions.py        # Niveles de acceso
│   │   └── audit.py              # Log de acciones
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── db.py                 # SQLite manager
│   │   ├── session.py            # Gestión de sesiones
│   │   └── models.py             # Modelos de datos
│   │
│   └── api/
│       ├── __init__.py
│       ├── chat.py               # Endpoints de chat
│       ├── sessions.py           # Endpoints de sesiones
│       ├── files.py              # Endpoints de archivos
│       └── admin.py              # Endpoints de administración
│
├── frontend/
│   └── ... (React app - Sprint 3)
│
├── specialties/
│   ├── default.json
│   ├── legal-laboral.json
│   └── baros.json
│
├── CONCEPTO.md                   # Visión general
└── DESIGN.md                     # Este archivo (especificación técnica)
```

---

## 8. Implementación — Checklist para Trantor

### Fase 1 — Base (día 1-2)

- [ ] `backend/config.py` — Configuración
- [ ] `backend/requirements.txt` — Dependencias
- [ ] `backend/memory/db.py` — SQLite init + schema
- [ ] `backend/memory/models.py` — Data classes
- [ ] `backend/memory/session.py` — CRUD sesiones
- [ ] `backend/main.py` — FastAPI app básica

### Fase 2 — LLM (día 2-3)

- [ ] `backend/llm/client.py` — Conexión Ollama
- [ ] `backend/llm/prompts.py` — System prompt builder
- [ ] `backend/llm/parser.py` — Parseo de tool calls
- [ ] Probar chat básico: mensaje → LLM → respuesta

### Fase 3 — Tools (día 3-5)

- [ ] `backend/tools/registry.py` — Registro de herramientas
- [ ] `backend/tools/orchestrator.py` — Ejecutor
- [ ] `backend/tools/file_tools.py` — Archivos
- [ ] `backend/tools/db_tools.py` — BD
- [ ] `backend/tools/web_tools.py` — Web
- [ ] Probar: LLM llama herramienta → ejecuta → devuelve resultado

### Fase 4 — Seguridad (día 5-6)

- [ ] `backend/security/sandbox.py` — Sandbox de archivos
- [ ] `backend/security/permissions.py` — Niveles de acceso
- [ ] `backend/security/audit.py` — Log de auditoría
- [ ] Probar restricciones de seguridad

### Fase 5 — API (día 6-7)

- [ ] `backend/api/chat.py` — Endpoint chat
- [ ] `backend/api/sessions.py` — Endpoint sesiones
- [ ] `backend/api/files.py` — Endpoint archivos
- [ ] `backend/api/admin.py` — Endpoint admin
- [ ] Probar flujo completo: API → LLM → Tool → Response
