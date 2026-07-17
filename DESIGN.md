# 🧠 R2 Hub — Technical Specification

> **Versión:** 2.0  
> **Arquitectura:** Hub + Agentes Independientes  
> **Estado:** Reinicio — diseño desde cero

---

## 1. Arquitectura General

```
┌────────────────────────────────────────────────────────────┐
│                        R2 HUB                              │
│  FastAPI :8234                                             │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ AgentManager  │  │  ProcessPool │  │  Hub UI (S3) │     │
│  │ - create      │  │  - start     │  │  - dashboard  │     │
│  │ - delete      │  │  - stop      │  │  - wizard     │     │
│  │ - configure   │  │  - restart   │  │  - logs       │     │
│  │ - list        │  │  - health    │  │  - settings   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘     │
│         │                 │                                 │
└─────────┼─────────────────┼─────────────────────────────────┘
          │                 │
          │      HTTP (localhost)
          │                 │
┌─────────▼─────────────────▼─────────────────────────────────┐
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │  🤖 Agente A   │  │  🤖 Agente B   │  │  🤖 Agente C   │  │
│  │  FastAPI:9001   │  │  FastAPI:9002   │  │  FastAPI:9003   │  │
│  │                 │  │                 │  │                 │  │
│  │  /api/v1/chat  │  │  /api/v1/chat  │  │  /api/v1/chat  │  │
│  │  /api/v1/health │  │  /api/v1/health │  │  /api/v1/health │  │
│  │  /api/v1/session│  │  /api/v1/session│  │  /api/v1/session│  │
│  │                 │  │                 │  │                 │  │
│  │  memory.db     │  │  memory.db     │  │  memory.db     │  │
│  │  (SQLite)       │  │  (SQLite)       │  │  (SQLite)       │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────┘

                ┌──────────────────────────────────┐
                │   Proveedores Externos            │
                │                                  │
                │   Ollama   → localhost:11434      │
                │   OpenAI   → api.openai.com       │
                │   Anthropic → api.anthropic.com  │
                │   Google   → generativelanguage  │
                │   Otros    → configurables       │
                └──────────────────────────────────┘
```

---

## 2. Hub — API Endpoints

### 2.1 Gestión de Agentes

```yaml
GET  /api/v1/hub/agents
  → Lista todos los agentes con estado
  Response: [
    {
      "name": "r2-prime",
      "status": "online",       # online | offline | starting | error
      "port": 9001,
      "pid": 12345,
      "uptime": 3600,
      "memory_mb": 45.2,
      "cpu_percent": 2.1,
      "disk_mb": 128,
      "description": "Asistente personal",
      "created_at": "2026-07-17T05:00:00Z"
    },
    ...
  ]

POST /api/v1/hub/agents
  → Crea un nuevo agente
  Body: {
    "name": "legal-assistant",
    "description": "Abogado laboral",
    "personality": {
      "tone": "professional",
      "formality": "usted",
      "humor": "none",
      "empathy": "professional"
    },
    "system_prompt": "Eres un abogado senior...",
    "llm": {
      "provider": "ollama",
      "model": "qwen2.5:7b",
      "temperature": 0.3
    },
    "tools": ["read_file", "write_file", "search_web"],
    "security_level": 2,
    "sandbox_paths": ["~/r2-hub/agents/legal-assistant/data/"],
    "channels": {
      "web": true,
      "whatsapp": {"enabled": false}
    }
  }
  Response: {
    "name": "legal-assistant",
    "port": 9002,
    "dir": "~/r2-hub/agents/legal-assistant/",
    "status": "starting",
    "chat_url": "http://localhost:9002/chat"
  }

DELETE /api/v1/hub/agents/{name}
  → Elimina un agente (lo detiene + archiva su directorio)
  
POST /api/v1/hub/agents/{name}/start
  → Inicia un agente que está offline
  
POST /api/v1/hub/agents/{name}/stop
  → Detiene un agente graceful (SIGTERM)
  
POST /api/v1/hub/agents/{name}/restart
  → Detiene + inicia

GET /api/v1/hub/agents/{name}/config
  → Devuelve el config.yaml del agente
  
PUT /api/v1/hub/agents/{name}/config
  → Actualiza config (requiere restart)
```

### 2.2 Monitoreo y Logs

```yaml
GET /api/v1/hub/agents/{name}/logs
  → Logs en tiempo real del agente
  Query: ?tail=50&since=2026-07-17T05:00:00Z
  
GET /api/v1/hub/agents/{name}/stats
  → Estadísticas: tokens usados, tools ejecutadas, conversaciones

GET /api/v1/hub/health
  → Health general del Hub + agentes
```

### 2.3 Enrutamiento al chat del agente

```yaml
POST /api/v1/hub/proxy/{agent_name}/chat
  → Proxy: recibe mensaje, lo reenvía al agente, devuelve respuesta
  → Útil para el frontend sin saber el puerto del agente
```

---

## 3. Agent Engine (cada agente)

Cada agente ejecuta el mismo **engine base** con su propia configuración.

### 3.1 API de cada agente

```yaml
POST /api/v1/chat
  Body (multipart): {
    "session_id": str | None,     # None = nueva sesión
    "message": str,
    "user_id": str,
    "files": [File] | None       # Archivos adjuntos
  }
  Response: {
    "session_id": str,
    "reply": str,
    "tools_used": list[str],
    "tokens_used": int,
    "attachments": [             # Archivos recibidos
      {"id": str, "name": str, "type": str, "size": int}
    ]
  }

POST /api/v1/chat/simple          # Sin archivos, solo texto
  Body: {
    "session_id": str | None,
    "message": str,
    "user_id": str
  }
  Response: {
    "session_id": str,
    "reply": str,
    "tools_used": list[str],
    "tokens_used": int
  }

GET  /api/v1/sessions
  → Lista sesiones del agente

POST /api/v1/upload
  → Subir archivo al data/ del agente
  
GET  /api/v1/files
  → Listar archivos en data/ del agente

GET  /api/v1/files/{id}
  → Descargar archivo

DELETE /api/v1/files/{id}
  → Eliminar archivo

GET  /api/v1/health
  → { "status": "ok", "uptime": 3600, "model": "qwen2.5:7b",
      "files_count": int, "sessions_active": int }
```

### 3.2 Componentes internos (engine template)

```python
# templates/agent_main.py
#
# Cada agente recibe UNA COPIA de este archivo.
# Se puede modificar sin afectar a otros agentes.

import os, sys, yaml
from pathlib import Path

AGENT_DIR = Path(__file__).parent        # ~/r2-hub/agents/{name}/
CONFIG = yaml.safe_load((AGENT_DIR / "config.yaml").read_text())

app = FastAPI(title=CONFIG["agent"]["name"])

# ── LLM Adapter ──────────────────────────────────
llm = LLMAdapter(
    provider=CONFIG["llm"]["provider"],
    model=CONFIG["llm"]["model"],
    api_key=CONFIG["llm"].get("api_key"),  # ← Para OpenAI, Anthropic, etc.
    host=CONFIG["llm"].get("host", "http://localhost:11434"),
    temperature=CONFIG["llm"].get("temperature", 0.7),
)

# ── Tools ─────────────────────────────────────────
tool_registry = ToolRegistry(CONFIG["tools"]["allow"])
tool_registry.load_base_tools()
if (AGENT_DIR / "tools").exists():
    tool_registry.load_custom_tools(AGENT_DIR / "tools")

orchestrator = ToolOrchestrator(tool_registry)

# ── Memory ────────────────────────────────────────
db = Database(AGENT_DIR / "memory.db")
db.init_schema()

# ── Security ──────────────────────────────────────
sandbox = Sandbox(CONFIG["security"]["sandbox"]["paths"])
permissions = PermissionEnforcer(CONFIG["security"]["level"])
audit = AuditLogger(AGENT_DIR / "logs" / "audit.log")


@app.post("/api/v1/chat")
async def chat(session_id: str = None, message: str = None, user_id: str = "default"):
    if not session_id:
        session = db.create_session(user_id)
        session_id = session.id
    else:
        session = db.get_session(session_id)
    
    # 1. Construir mensajes
    messages = [
        {"role": "system", "content": CONFIG["personality"]["system_prompt"]},
        *session.get_recent(limit=20),
        {"role": "user", "content": message},
    ]
    
    # 2. Llamar LLM con tools disponibles
    tools = tool_registry.to_ollama_format()
    response = await llm.chat(messages, tools=tools)
    
    # 3. Procesar tool calls
    tools_used = []
    if response.tool_calls:
        for tc in response.tool_calls:
            result = orchestrator.execute(tc, user_id, permissions)
            audit.log(user_id, tc["function"]["name"], result)
            tools_used.append(tc["function"]["name"])
            
            messages.append({
                "role": "tool",
                "content": json.dumps(result),
                "name": tc["function"]["name"],
            })
        
        # Respuesta final con resultados
        final = await llm.chat(messages)
        reply = final.content
    else:
        reply = response.content
    
    # 4. Guardar en BD
    session.add_message("user", message)
    session.add_message("assistant", reply, tools_used)
    
    return {
        "session_id": session.id,
        "reply": reply,
        "tools_used": tools_used,
        "tokens_used": response.tokens,
        "attachments": attachments_received,   # Archivos recibidos
    }


# ── Archivos ────────────────────────────────────

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile):
    """Sube un archivo al data/ del agente."""
    ext = Path(file.filename).suffix.lower()
    allowed = CONFIG["files"]["allowed_extensions"]
    
    if ext not in allowed:
        raise HTTPException(400, f"Extensión no permitida: {ext}")
    
    file_id = str(uuid.uuid4())
    file_path = AGENT_DIR / "data" / f"{file_id}{ext}"
    file_path.write_bytes(await file.read())
    
    return {"id": file_id, "name": file.filename, "path": str(file_path), "size": file_path.stat().st_size}


@app.get("/api/v1/files")
async def list_files():
    """Lista archivos en data/ del agente."""
    data_dir = AGENT_DIR / "data"
    files = []
    for f in data_dir.iterdir():
        if f.is_file():
            files.append({"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return {"files": files}


@app.get("/api/v1/files/{file_id}")
async def download_file(file_id: str):
    """Descarga un archivo del data/ del agente."""
    data_dir = AGENT_DIR / "data"
    for f in data_dir.iterdir():
        if f.stem == file_id:
            return FileResponse(f)
    raise HTTPException(404, "Archivo no encontrado")


@app.delete("/api/v1/files/{file_id}")
async def delete_file(file_id: str):
    """Elimina un archivo del data/ del agente."""
    data_dir = AGENT_DIR / "data"
    for f in data_dir.iterdir():
        if f.stem == file_id:
            f.unlink()
            return {"status": "deleted", "file": f.name}
    raise HTTPException(404, "Archivo no encontrado")


@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "name": CONFIG["agent"]["name"],
        "uptime": time.time() - start_time,
        "model": CONFIG["llm"]["model"],
        "sessions_active": db.count_active_sessions(),
    }
```

### 3.3 Gestión de API Keys

Cada agente almacena sus propias API keys en su `config.yaml`. El Hub provee una interfaz para gestionarlas de forma segura.

#### Config de LLM con proveedores externos

```yaml
# ~/r2-hub/agents/marketing-bot/config.yaml
llm:
  provider: openai          # ollama | openai | anthropic | google | custom
  api_key: "sk-proj-..."    # ← Key del proveedor
  model: gpt-4o              # Modelo específico
  temperature: 0.8
  # host: solo para Ollama o endpoints custom

# Opción: keys desde variable de entorno (más seguro)
# api_key: "${OPENAI_API_KEY}"
```

#### Proveedores soportados

| Provider | Config | API Key |
|----------|--------|---------|
| Ollama | Local | No necesita key |
| OpenAI | `gpt-4o`, `gpt-4`, `gpt-3.5-turbo` | `sk-...` |
| Anthropic | `claude-opus-4`, `claude-sonnet-4` | `sk-ant-...` |
| Google | `gemini-2.0-flash`, `gemini-2.0-pro` | `AIza...` |
| Custom | Cualquier endpoint compatible con OpenAI API | Según el provider |

#### Seguridad de keys

```yaml
# Opción 1: En config.yaml (simple, visible)
llm:
  provider: openai
  api_key: "sk-proj-abc123..."

# Opción 2: Variable de entorno (más seguro)
llm:
  provider: openai
  api_key: "${OPENAI_API_KEY}"   # Se resuelve al iniciar el agente

# Opción 3: Keychain del sistema (recomendado)
# El Hub almacena keys en el keychain del SO
# El agente las pide al iniciar
```

#### El Hub también puede gestionar keys globales

```yaml
# config.yaml del Hub
hub:
  api_keys:
    openai: "${OPENAI_API_KEY}"       # Key global del Hub
    anthropic: "${ANTHROPIC_API_KEY}"

  api_key_inheritance: true   # Los agentes heredan keys del Hub
                              # si no especifican las suyas propias
```

### 3.4 Tool Registry (por agente)

Cada agente tiene su propio registro de tools. Las tools base son las mismas, pero cada agente puede **añadir o denegar** las que quiera.

```python
class ToolRegistry:
    """Registro de herramientas disponible para UN agente."""
    
    BASE_TOOLS = {
        "read_file": FileReadTool,
        "write_file": FileWriteTool,
        "list_files": FileListTool,
        "search_web": WebSearchTool,
        "fetch_url": WebFetchTool,
        "save_memory": MemorySaveTool,
        "get_memory": MemoryGetTool,
        "query_db": DBQueryTool,
        "read_document": DocumentReadTool,    # PDF, DOCX, TXT, CSV, XLSX
        "read_image": ImageReadTool,          # Visión con LLM
        "read_audio": AudioReadTool,          # Transcripción whisper
        "list_attachments": AttachmentsListTool,
        "exec_command": ExecCommandTool,      # Solo Nivel 3
        "send_whatsapp": WhatsAppSendTool,
    }
    
    def __init__(self, allow_list: list[str], deny_list: list[str] = None):
        self.deny = set(deny_list or [])
        self.allow = set(allow_list)
        
        self.tools = {}
        for name, tool_class in self.BASE_TOOLS.items():
            if name in self.deny:
                continue
            if "*" in self.allow or name in self.allow:
                self.tools[name] = tool_class()
        
        # Cargar tools personalizadas del agente
        custom_dir = AGENT_DIR / "tools"
        if custom_dir.exists():
            self._load_custom(custom_dir)
```

### 3.4 Agente puede tener tools personalizadas

Si el usuario (o el Hub) pone archivos Python en `~/r2-hub/agents/{name}/tools/`, se cargan automáticamente:

```python
# ~/r2-hub/agents/baros/tools/consultar_stock.py

@tool(name="consultar_stock", description="Consulta el stock de un producto")
def consultar_stock(producto: str, cantidad: int = None) -> dict:
    """Tool específica de BarOS."""
    db = connect_to_local_db()
    return db.query("SELECT * FROM stock WHERE producto = ?", [producto])
```

### 3.6 Memoria (SQLite) — por agente

Cada agente tiene su propio `memory.db`:

```sql
-- ~/r2-hub/agents/r2-prime/memory.db
-- IDÉNTICO esquema, pero datos completamente independientes

CREATE TABLE sessions (...);
CREATE TABLE messages (...);
CREATE TABLE long_term_memory (...);
CREATE TABLE audit_log (...);
```

---

## 4. AgentManager — El corazón del Hub

### 4.1 Creación de agente

```python
class AgentManager:
    """Gestiona los agentes en el sistema.
    
    Cada agente vive en la ubicación que el usuario eligió.
    El Hub mantiene un registro de dónde está cada uno.
    """
    
    TEMPLATES_DIR = Path.home() / "AgentOS" / "templates"
    PORT_START = 9000
    _port_lock = Lock()
    _registry_path = Path.home() / "AgentOS" / "agents.json"
    
    def __init__(self):
        self.agents = self._load_registry()
    
    def create(self, name: str, install_path: str, config: dict) -> AgentInfo:
        """Crea un nuevo agente en la ubicación que el usuario eligió."""
        
        # 1. Validar nombre
        if not name or len(name.strip()) == 0:
            raise ValueError("El nombre del agente no puede estar vacío")
        
        agent_dir = Path(install_path) / name
        if agent_dir.exists():
            raise FileExistsError(f"Ya existe un agente llamado '{name}' en esa ubicación")
        
        # 2. Crear estructura de directorios
        agent_dir.mkdir(parents=True)
        (agent_dir / "data").mkdir()
        (agent_dir / "logs").mkdir()
        (agent_dir / "tools").mkdir()
        
        # 3. Asignar puerto único
        port = self._next_port()
        
        # 4. Generar config.yaml
        config["agent"]["name"] = name
        config["agent"]["install_path"] = str(agent_dir)
        config["agent"]["port"] = port
        config["agent"]["status"] = "offline"
        (agent_dir / "config.yaml").write_text(yaml.dump(config))
        
        # 5. Copiar engine template
        template = self.TEMPLATES_DIR / "agent_main.py"
        shutil.copy(template, agent_dir / "agent_main.py")
        
        # 6. Copiar componentes base (llm/, tools/, security/, memory/)
        self._copy_template_dir("llm", agent_dir)
        self._copy_template_dir("tools", agent_dir)
        self._copy_template_dir("security", agent_dir)
        self._copy_template_dir("memory", agent_dir)
        
        # 7. Inicializar BD
        db = Database(agent_dir / "memory.db")
        db.init_schema()
        
        # 8. Crear entry point (script)
        self._create_run_script(agent_dir, port)
        
        # 9. Registrar en el Hub
        info = AgentInfo(
            name=name,
            port=port,
            dir=agent_dir,
            install_path=str(agent_dir),
            status="offline"
        )
        self.agents[name] = info
        self._save_registry()
        
        return info
    
    def delete(self, name: str, archive: bool = True):
        """Detiene el agente y archiva o elimina su directorio."""
        if name not in self.agents:
            raise KeyError(f"Agente '{name}' no encontrado")
        
        info = self.agents[name]
        self.stop(name)
        
        if archive:
            # Mover a una carpeta de backups en lugar de borrar
            backup_dir = Path.home() / "AgentOS" / "archived" / name
            shutil.move(info.dir, backup_dir)
        else:
            shutil.rmtree(info.dir)
        
        del self.agents[name]
        self._save_registry()
    
    def _load_registry(self) -> dict:
        if self._registry_path.exists():
            data = json.loads(self._registry_path.read_text())
            return {k: AgentInfo(**v) for k, v in data.items()}
        return {}
    
    def _save_registry(self):
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.__dict__ for k, v in self.agents.items()}
        self._registry_path.write_text(json.dumps(data, indent=2))
    
    def _next_port(self) -> int:
        with self._port_lock:
            used = {a.port for a in self.agents.values()}
            port = self.PORT_START
            while port in used:
                port += 1
            return port
```

### 4.2 Ciclo de vida del proceso

```python
class AgentProcess:
    """Maneja el subproceso de un agente."""
    
    def __init__(self, name: str, port: int, agent_dir: Path):
        self.name = name
        self.port = port
        self.agent_dir = agent_dir
        self.process: subprocess.Popen | None = None
        self.start_time: float | None = None
    
    def start(self):
        """Lanza el agente como subproceso independiente."""
        log_file = open(self.agent_dir / "logs" / "agent.log", "a")
        
        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "agent_main:app",
                f"--port={self.port}",
                "--host=127.0.0.1",
                "--log-level=info",
            ],
            cwd=str(self.agent_dir),
            stdout=log_file,
            stderr=log_file,
            # Grupo de proceso independiente
            start_new_session=True,
        )
        self.start_time = time.time()
        
        # Esperar a que responda health check
        self._wait_ready(timeout=10)
    
    def stop(self, timeout=5):
        """Detiene el agente graceful."""
        if self.process is None:
            return
        
        # SIGTERM primero
        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # SIGKILL si no responde
            self.process.kill()
            self.process.wait()
        
        self.process = None
        self.start_time = None
    
    def restart(self):
        self.stop()
        self.start()
    
    @property
    def is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def _wait_ready(self, timeout=10):
        """Espera a que el health check responda."""
        import httpx
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = httpx.get(f"http://127.0.0.1:{self.port}/api/v1/health", timeout=1)
                if r.status_code == 200:
                    return True
            except:
                pass
            time.sleep(0.5)
        raise TimeoutError(f"Agente {self.name} no respondió en {timeout}s")
```

### 4.3 Health Checker continuo

```python
class HealthChecker:
    """Monitorea todos los agentes en un loop async."""
    
    def __init__(self, manager: AgentManager, check_interval=15):
        self.manager = manager
        self.interval = check_interval
    
    async def run(self):
        while True:
            for agent in self.manager.list():
                if agent.status == "online":
                    alive = await self._check(agent)
                    if not alive and agent.config.get("auto_restart", True):
                        logger.warning(f"{agent.name} offline → reiniciando")
                        self.manager.restart(agent.name)
            await asyncio.sleep(self.interval)
    
    async def _check(self, agent) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"http://127.0.0.1:{agent.port}/api/v1/health",
                    timeout=3
                )
                return r.status_code == 200
        except:
            return False
```

---

## 5. Estructura de Archivos (Hub)

```
r2-autonomous/
├── CONCEPTO.md                       ← Visión (este doc)
├── DESIGN.md                         ← Especificación técnica (este doc)
├── SPRINTS.md                        ← Plan de desarrollo
│
├── hub/                              ← Backend del Hub
│   ├── main.py                       ← FastAPI :8234
│   ├── config.py                     ← Config del Hub
│   ├── requirements.txt
│   │
│   ├── agent_manager.py              ← Crear/detener/gestión
│   ├── agent_process.py              ← Manejo de subprocesos
│   ├── health_checker.py             ← Monitoreo continuo
│   │
│   ├── api/
│   │   ├── agents.py                 ← CRUD de agentes
│   │   ├── proxy.py                  ← Proxy al chat del agente
│   │   └── admin.py                  ← Config del Hub
│   │
│   └── templates/                    ← Plantillas para nuevos agentes
│       ├── agent_main.py             ← Engine base
│       ├── default_config.yaml       ← Config base
│       └── run.sh / run.bat          ← Script de inicio
│
├── frontend/                         ← React (Hub UI)
│   └── ...
│
└── config.yaml                       ← Config global del Hub
    # Puerto base, directorio de agentes, etc.
```

---

## 6. Seguridad

### 6.1 Aislamiento entre agentes

```
┌──────────────────────────────────────────────────┐
│  🔒 AISLAMIENTO                                  │
│                                                   │
│  Procesos:   Cada agente en su propio proceso     │
│              PID separado, memoria separada       │
│                                                   │
│  Archivos:   Cada agente SOLO ve su directorio    │
│              ~/r2-hub/agents/{name}/              │
│              No puede leer archivos de otros      │
│                                                   │
│  Red:        Cada agente en su puerto             │
│              Solo localhost, no expuesto          │
│                                                   │
│  BD:         memory.db propia                     │
│              No comparte sesiones con nadie       │
│                                                   │
│  Si uno se cae → los otros siguen funcionando    │
└──────────────────────────────────────────────────┘
```

### 6.2 Sandbox de cada agente

El sandbox del agente restringe el acceso a archivos dentro de su directorio:

```python
# Cada agente tiene su propio Sandbox
sandbox_paths = [
    "~/r2-hub/agents/r2-prime/data/",    # Solo sus datos
]
```

Si un agente necesita acceso a otras rutas (ej. R2 PRIME accede a `~/Trantor/`), se configura explícitamente en su `config.yaml`.

### 6.3 Niveles de acceso (por agente)

Cada agente tiene su propio nivel de seguridad, configurable independientemente.

El agente R2 PRIME de Xavier puede tener Nivel 3 (todo). El agente de un cliente solo Nivel 1.

---

## 7. Models — Config del Hub

```yaml
# config.yaml — R2 Hub global
hub:
  name: "R2 Hub"
  port: 8234
  agents_dir: "~/r2-hub/agents"
  templates_dir: "~/r2-hub/templates"
  log_dir: "~/r2-hub/logs"

  port_range:
    start: 9000
    end: 9999

  health_check:
    interval_seconds: 15
    timeout_seconds: 5
    auto_restart: true

  llm_pool:                       # Pool compartido de Ollama
    enabled: false                # (futuro)
    models:
      - qwen2.5:7b
      - deepseek-coder:6.7b

  web:                            # Frontend
    enabled: true
    port: 3000
```

---

## 8. Diferencias clave con la v1

| Componente | v1 (vieja) | v2 (Hub) |
|------------|-----------|----------|
| `backend/` | Un solo backend monolítico | `hub/` (gestión) + cada agente su propio backend |
| `main.py` | Un solo entry point | Hub en :8234, cada agente su propio `agent_main.py` en su puerto |
| `memory/` | Una BD global | Cada agente su `memory.db` |
| `tools/` | Un registry global | Cada agente su propio registry + tools personalizadas |
| `specialties/` | JSON de personalidades | Agentes completos con directorio propio |
| `channels/` | Canales globales para el único agente | Cada agente decide sus canales |
| `security/` | Una configuración | Cada agente su propio nivel y sandbox |
| `api/` | APIs del agente | Hub tiene APIs de gestión + cada agente sus APIs de chat |

---

## 9. Checklist de implementación

### Hub (Sprint 1)
- [ ] `hub/main.py` — FastAPI en :8234
- [ ] `hub/agent_manager.py` — CRUD de agentes
- [ ] `hub/agent_process.py` — Subprocesos (start/stop/restart)
- [ ] `hub/health_checker.py` — Monitoreo continuo
- [ ] `hub/api/agents.py` — Endpoints REST de gestión
- [ ] `hub/templates/agent_main.py` — Engine template
- [ ] `hub/templates/default_config.yaml` — Config template

### Engine base (Sprint 1-2)
- [ ] LLMAdapter + Ollama (desde v1, reusable)
- [ ] ToolRegistry + ToolOrchestrator (desde v1, reusable)
- [ ] Sandbox + Permissions + Audit (desde v1, reusable)
- [ ] Database (SQLite, desde v1, reusable)
- [ ] Agent engine con tool calling nativo

### Frontend (Sprint 3)
- [ ] Dashboard con lista de agentes
- [ ] Wizard de creación de agente
- [ ] Chat view (enruta al agente seleccionado)
- [ ] Logs en vivo
- [ ] Config editor
