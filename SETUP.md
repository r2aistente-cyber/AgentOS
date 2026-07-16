# ⚙️ R2 Autonomous — Sistema de configuración

> **Versión:** 1.0
> **Autor:** R2 PRIME (Concepto)
> **Propósito:** Cómo se crean los agentes, se configuran proveedores y canales.
> **Flujo:** Setup wizard (primer inicio) → Archivos de configuración → Canales

---

## 1. Estructura de archivos del agente

Todo lo que R2 necesita saber está en una carpeta:

```text
~/.r2/                          ← Carpeta raíz (como ~/.openclaw/)
├── config.yaml                 ← Configuración global
├── specialties/                ← Especialidades del agente
│   ├── default.json            ← Especialidad base
│   ├── legal-laboral.json      ← Especialidad legal
│   └── baros.json              ← Especialidad bar
├── memory.db                   ← SQLite (sesiones, memoria, auditoría)
├── logs/
│   └── r2-server.log
└── channels/
    ├── whatsapp/               ← Estado de WhatsApp Web
    │   └── auth_info.json
    └── telegram/               ← Estado de Telegram
        └── bot_session.json
```

---

## 2. Configuración global (config.yaml)

```yaml
# ~/.r2/config.yaml

# ─── Proveedor LLM ───────────────
llm:
  provider: ollama          # ollama | openai | anthropic | openrouter
  model: qwen2.5:7b         # Nombre del modelo
  temperature: 0.7
  max_tokens: 4096

  # Solo para Ollama:
  ollama:
    host: http://localhost:11434
  
  # Solo para OpenAI/Anthropic/OpenRouter:
  # api:
  #   key: sk-...            # Guardada en keychain, NO en texto plano
  #   endpoint: https://api.openai.com/v1

# ─── Canales ──────────────────────
channels:
  web: true                 # Webchat siempre activo
  whatsapp:
    enabled: false
    phone: "+573192270876"   # Número del bot
  telegram:
    enabled: false
    bot_token: ""            # Token del bot

# ─── Seguridad ────────────────────
security:
  default_level: 2          # Nivel de permiso por defecto
  sandbox_paths:
    - ~/Trantor/DiscoE/
    - ~/Documents/R2/
    - /tmp/r2-temp/
  require_confirmation:
    - send_whatsapp
    - delete_file
  
  users:
    - id: xavier
      name: Xavier
      level: 3              # Dueño: acceso total
    - id: luisa
      name: Luisa
      level: 1              # Solo lectura

# ─── Especialidad activa ──────────
active_specialty: default
```

---

## 3. Especialidades (archivos de agente)

Cada especialidad es un archivo JSON que define **quién es el agente**:

```json
{
  "id": "legal-laboral",
  "name": "Asistente Legal Laboral",
  "version": "1.0",
  
  "personality": {
    "system_prompt": "Eres un abogado senior con 20 años de experiencia...",
    "tone": "formal",
    "address_form": "usted",
    "humor": "none",
    "empathy": "professional"
  },
  
  "model": {
    "provider": "ollama",
    "model": "qwen2.5:7b",
    "temperature": 0.3
  },
  
  "tools": {
    "allow": ["*"],                    ← Todas las herramientas base
    "extra": [],
    "deny": ["send_whatsapp"]          ← Esta especialidad no envía WhatsApp
  },
  
  "knowledge": {
    "documents": [
      "~/Trantor/DiscoE/leyes/CST.pdf",
      "~/Trantor/DiscoE/jurisprudencia/"
    ],
    "citations_required": true
  },
  
  "sandbox": {
    "paths": [
      "~/Trantor/DiscoE/casos/",
      "~/Trantor/DiscoE/plantillas/"
    ]
  }
}
```

**Cada especialidad puede tener:**
- Su propio modelo y temperatura
- Sus propias herramientas (una especialidad legal no necesita las mismas que BarOS)
- Su propio sandbox
- Su propia personalidad

**Cambiar de especialidad = cambiar el JSON activo.** Sin reiniciar nada.

---

## 4. Setup Wizard — Primer inicio

Cuando abres R2 por primera vez, aparece esto:

### Pantalla 1: Bienvenida

```
┌─────────────────────────────────────────────┐
│  🚀 Bienvenido a R2 Autonomous              │
│                                             │
│  Tu asistente personal, 100% local.         │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Vamos a configurar 3 cosas:           │  │
│  │                                       │  │
│  │  ① Cerebro (LLM) — ¿local o API?     │  │
│  │  ② Canales — ¿WhatsApp, Telegram?    │  │
│  │  ③ Personalidad — ¿qué quieres que   │  │
│  │     sea tu agente?                    │  │
│  │                                       │  │
│  │  Todo se puede cambiar después. ⚙️    │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  🔍 Detectando componentes...          │  │
│  │  ✓ FastAPI server... listo            │  │
│  │  ⏳ Ollama... no encontrado            │  │
│  └───────────────────────────────────────┘  │
│                                             │
│           [Comenzar ▶]                       │
└─────────────────────────────────────────────┘
```

### Pantalla 2: Elegir proveedor LLM

```
┌─────────────────────────────────────────────┐
│  ① ¿Cómo quieres que piense R2?            │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🤖 Ollama (local, gratis)         │ ◄┐  │
│  │  ✅ Sin internet                    │  │  │
│  │  ✅ Sin API keys                    │  │  │
│  │  ⚡ Descarga ~4 GB (una vez)        │  ┘  │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  ☁️ OpenAI (GPT-4o)                 │    │
│  │  ⚡ Más potente                      │    │
│  │  💰 ~$20/mes                        │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  ☁️ Anthropic (Claude Sonnet)       │    │
│  │  ⚡ Mejor para documentos largos    │    │
│  │  💰 ~$20/mes                        │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🔀 OpenRouter (el que quieras)     │    │
│  │  ⚡ Cualquier modelo                │    │
│  │  💰 Pay-as-you-go                   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [Atrás]              [Siguiente ▶]          │
└─────────────────────────────────────────────┘
```

**Si elige Ollama:**

```
┌─────────────────────────────────────────────┐
│  Instalando Ollama...                        │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  📦 Descargando Ollama...             │  │
│  │  ████████████░░░░░░ 68%              │  │
│  │                                       │  │
│  │  Después: descargar modelo            │  │
│  │  (Qwen2.5:7b ~4 GB)                   │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Cancelar]       [Descargar en fondo ⏳]    │
└─────────────────────────────────────────────┘
```

**Si elige OpenAI/Anthropic:**

```
┌─────────────────────────────────────────────┐
│  Ingresa tu API Key                         │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Provedor:  OpenAI                     │  │
│  │  Modelo:    [gpt-4o              ▼]   │  │
│  │                                       │  │
│  │  🔑 API Key                           │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  sk-proj-xxxxxxxxxxxxxxxx      │  │  │
│  │  └─────────────────────────────────┘  │  │
│  │                                       │  │
│  │  💳 ¿Dónde conseguirla?               │  │
│  │  platform.openai.com/api-keys        │  │
│  │                                       │  │
│  │  🔒 Se guarda en el Keychain de macOS │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Atrás]              [Probar conexión ▶]   │
└─────────────────────────────────────────────┘
```

### Pantalla 3: Configurar WhatsApp

```
┌─────────────────────────────────────────────┐
│  ② ¿Quieres que R2 hable por WhatsApp?     │
│                                             │
│  📱 WhatsApp                                │
│  ┌─────────────────────────────────────┐    │
│  │  ☑ Activar WhatsApp                │    │
│  │  📞 Número del bot: [+57 323...]  │    │
│  │                                     │    │
│  │  ⚠️ Se abrirá una ventana con     │    │
│  │  un código QR. Escanéalo con       │    │
│  │  WhatsApp en tu celular.           │    │
│  │                                     │    │
│  │  🔍 Estado: [Conectar ▼]          │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  Activar después                               │
│                                             │
│  [Atrás]              [Siguiente ▶]          │
└─────────────────────────────────────────────┘
```

**Cuando hace clic en "Conectar":**

```
┌─────────────────────────────────────────────┐
│  📱 Escanea este código QR                  │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │                                       │  │
│  │         ┌─────────────────┐           │  │
│  │         │                 │           │  │
│  │         │   █▀█ █▀█ ▄▀▄  │           │  │
│  │         │   ▀▀█ █ █ █ █  │           │  │
│  │         │   █▀▀ ▀▀▀ ▀▀▀  │           │  │
│  │         └─────────────────┘           │  │
│  │                                       │  │
│  │  Abre WhatsApp en tu celular →        │  │
│  │  Dispositivos vinculados →            │  │
│  │  Vincular dispositivo                 │  │
│  │                                       │  │
│  │  ⏳ Esperando escaneo...              │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Cancelar]                                  │
└─────────────────────────────────────────────┘
```

### Pantalla 4: Configurar Telegram

```
┌─────────────────────────────────────────────┐
│  ② (opcional) ¿Telegram?                    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  ☐ Activar Telegram                 │    │
│  │                                     │    │
│  │  🤖 Bot Token                       │    │
│  │  ┌─────────────────────────────┐   │    │
│  │  │  123456:ABCdefGHIjklMNO    │   │    │
│  │  └─────────────────────────────┘   │    │
│  │                                     │    │
│  │  💡 Cómo crear un bot:              │    │
│  │  1. Busca @BotFather en Telegram   │    │
│  │  2. /newbot → nombre → token       │    │
│  │  3. Copia el token aquí            │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [Atrás]              [Siguiente ▶]          │
└─────────────────────────────────────────────┘
```

### Pantalla 5: Crear agente (especialidad)

```
┌─────────────────────────────────────────────┐
│  ③ ¿Qué quieres que sea R2?                │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🎯 Asistente personal             │ ◄┐  │
│  │     General, como soy ahora         │  │  │
│  └─────────────────────────────────────┘  │  │
│                                           │  │
│  ┌─────────────────────────────────────┐  │  │
│  │  ⚖️ Asistente Legal (laboral)      │  │  │
│  │     Abogado senior, formal         │  ┘  │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🧾 BarOS (gestión de bares)        │    │
│  │     Bartender digital              │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  📢 Marketing Agent                 │    │
│  │     Community manager               │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🎨 Personalizado...                │    │
│  │     Crear desde cero                │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [Atrás]              [Siguiente ▶]          │
└─────────────────────────────────────────────┘
```

**Si elige personalizado:**

```
┌─────────────────────────────────────────────┐
│  Crea tu agente personalizado               │
│                                             │
│  Nombre del agente:                         │
│  ┌───────────────────────────────────────┐  │
│  │  Mi Asistente                         │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Tono:  ○ Formal  ○ Profesional  ● Cercano │
│  Tuteo: ○ Tutea   ● Usted                  │
│  Humor: ○ Nunca   ○ Poco   ● Natural       │
│                                             │
│  Descripción breve:                         │
│  ┌───────────────────────────────────────┐  │
│  │  "Eres un asistente amable que        │  │
│  │  ayuda con tareas diarias..."         │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Atrás]              [Crear agente ▶]       │
└─────────────────────────────────────────────┘
```

### Pantalla 6: ¡Listo!

```
┌─────────────────────────────────────────────┐
│  ✅ ¡R2 Autonomous está listo!              │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Resumen de configuración:            │  │
│  │                                       │  │
│  │  🧠 Cerebro: Ollama (Qwen2.5:7b)    │  │
│  │  💬 Chat web: ✅ Activo              │  │
│  │  📱 WhatsApp: ✅ Conectado           │  │
│  │  🤖 Telegram: ❌ Omitido             │  │
│  │  🎯 Agente: Asistente Legal          │  │
│  │  🔐 Nivel: 3 (Autónomo)             │  │
│  │                                       │  │
│  │  📁 Tus documentos en:               │  │
│  │  ~/Trantor/DiscoE/                  │  │
│  │  ~/Documents/R2/                    │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Puedes cambiar esto cuando quieras          │
│  desde ⚙️ Preferencias.                     │
│                                             │
│  [Empezar a hablar con R2 🚀]              │
└─────────────────────────────────────────────┘
```

---

## 5. Cómo detecta conexión a Ollama

```python
# backend/setup/detector.py
class Detector:
    """Detecta qué componentes están disponibles."""
    
    @staticmethod
    def detect_ollama() -> dict:
        """Verifica si Ollama está instalado y funcionando."""
        # 1. ¿Ollama está en PATH?
        has_ollama = shutil.which("ollama") is not None
        
        # 2. ¿Ollama server responde?
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            ollama_running = r.status_code == 200
            models = [m["name"] for m in r.json().get("models", [])]
        except:
            ollama_running = False
            models = []
        
        # 3. ¿Hay modelos descargados?
        has_models = len(models) > 0
        
        return {
            "installed": has_ollama,
            "running": ollama_running,
            "models": models,
            "has_models": has_models
        }
    
    @staticmethod
    def install_ollama() -> bool:
        """Descarga e instala Ollama automáticamente."""
        # macOS: descargar DMG
        url = "https://ollama.com/download/Ollama-darwin.zip"
        # Windows: https://ollama.com/download/OllamaSetup.exe
        # Linux: curl -fsSL https://ollama.com/install.sh | sh
        ...
    
    @staticmethod
    def pull_model(model: str, on_progress):
        """Descarga un modelo de Ollama con callback de progreso."""
        proc = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in proc.stdout:
            # Parsear progreso del output de Ollama
            if "pulling" in line:
                percent = extract_percent(line)
                on_progress(percent)
        ...
```

---

## 6. Cómo se conecta WhatsApp

```python
# backend/channels/whatsapp.py
import qrcode
from whatasapp import Client  # whatsapp-web.js wrapper

class WhatsAppChannel:
    def __init__(self, config_dir):
        self.client = Client(
            session_path=f"{config_dir}/channels/whatsapp/",
            # whatsapp-web.js guarda la sesión aquí
        )
    
    async def connect(self, on_qr):
        """Inicia conexión y pasa el QR a la UI."""
        self.client.on("qr", lambda qr: on_qr(qr))
        # on_qr() envía el QR a la app de Tauri
        # Tauri lo renderiza en pantalla
        
        self.client.on("ready", lambda: 
            self.save_session()  # Guarda sesión para reconectar
        )
        
        await self.client.start()
    
    async def send(self, to: str, message: str):
        """Envía mensaje de WhatsApp."""
        await self.client.send_message(to, message)
    
    async def listen(self, on_message):
        """Escucha mensajes entrantes y los envía al orquestador."""
        self.client.on("message", lambda msg:
            on_message({
                "from": msg.from_,
                "text": msg.body,
                "channel": "whatsapp",
                "timestamp": msg.timestamp
            })
        )
```

---

## 7. Cómo se conecta Telegram

```python
# backend/channels/telegram.py
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

class TelegramChannel:
    def __init__(self, bot_token: str):
        self.token = bot_token
        self.app = None
    
    async def connect(self):
        """Inicia el bot de Telegram."""
        self.app = Application.builder().token(self.token).build()
        
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_message
        ))
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
    
    async def handle_message(self, update: Update, context):
        """Un mensaje de Telegram entra al orquestador."""
        message = {
            "from": str(update.effective_user.id),
            "text": update.message.text,
            "channel": "telegram",
            "chat_id": update.effective_chat.id
        }
        # Enviar al orquestador
        response = await orchestrator.process(message)
        # Responder
        await update.message.reply_text(response)
    
    async def send(self, chat_id: str, text: str):
        await self.app.bot.send_message(chat_id=chat_id, text=text)
```

---

## 8. Resumen del flujo

```text
Usuario abre la app
       │
       ▼
┌───────────────────────┐
│ ¿Primera vez?         │
│ (existe ~/.r2/)       │──No──→ Ventana de chat directo
└───────────┬───────────┘
            │ Sí
            ▼
┌───────────────────────┐
│ Setup Wizard          │
│ 1. Detectar Ollama    │
│ 2. Elegir proveedor   │
│ 3. Conectar canales   │
│ 4. Crear agente       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Escribir config.yaml  │
│ Guardar especialidad  │
│ Iniciar servicios     │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ ✅ R2 listo           │
│ Ventana de chat       │
└───────────────────────┘
```

---

## 9. Preferencias (panel de configuración)

Desde la app, en cualquier momento:

```
⚙️ Preferencias

  🧠 Modelo
     → Cambiar proveedor (Ollama ↔ OpenAI ↔ Anthropic)
     → Cambiar modelo (qwen ↔ gpt-4o ↔ claude)
     → Ingresar/quitar API key
  
  📱 Canales
     → Conectar/desconectar WhatsApp
     → Escanear QR de nuevo
     → Conectar/desconectar Telegram
  
  🎯 Agente
     → Cambiar especialidad
     → Editar personalidad
     → Cargar documentos de conocimiento
  
  🔐 Seguridad
     → Subir/bajar nivel
     → Agregar/quitar carpetas del sandbox
     → Ver auditoría
  
  📦 Actualizaciones
     → Buscar actualización
     → Versión actual
```

---

## 10. Checklist para Trantor

### Fase 1 — Setup Wizard

- [ ] Pantalla de bienvenida + detección de componentes
- [ ] Selector de proveedor LLM (Ollama / OpenAI / Anthropic / OpenRouter)
- [ ] Input de API key con validación (probar conexión)
- [ ] Descarga de Ollama + modelo con progreso
- [ ] Conexión WhatsApp (mostrar QR en ventana)
- [ ] Conexión Telegram (input de bot token)
- [ ] Selector/creador de especialidad
- [ ] Resumen final y escritura de config.yaml

### Fase 2 — Config system

- [ ] `~/.r2/config.yaml` lectura/escritura
- [ ] `~/.r2/specialties/*.json` carga de especialidades
- [ ] Keychain macOS para API keys (no texto plano)
- [ ] Hot-reload de configuración (sin reiniciar)

### Fase 3 — Canales

- [ ] WhatsApp channel (whatsapp-web.js)
- [ ] Telegram channel (python-telegram-bot)
- [ ] Escucha mensajes entrantes → orquestador
- [ ] Envío de respuestas → canal correspondiente
