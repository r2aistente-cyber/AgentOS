# 🦀 R2 Autonomous — Desktop App Concept (Tauri)

> **Versión:** 2.0
> **Autor:** R2 PRIME (Concepto)
> **Propósito:** Especificación de la aplicación de escritorio nativa que reemplaza la terminal.
> **Framework:** Tauri 2.x + React + FastAPI

---

## 1. Filosofía de la app

```text
📱 COMO DEBERÍA SENTIRSE
─────────────────────────────────────────

  Como la app de ChatGPT, pero:
  ✅ 100% local (sin cuenta, sin internet)
  ✅ Abre al instante
  ✅ Cierra con Cmd+W
  ✅ Vuelve con Cmd+Space
  ✅ Se siente nativa en Mac
  ✅ Cambia de modelo en 1 clic
  ✅ Nueva sesión en 1 clic

  ❌ No como una página web en Chrome
  ❌ No como una terminal
  ❌ Sin pasos intermedios
```

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   TU MÁQUINA                         │
│                                                     │
│  ┌──────────────────────────┐  ┌─────────────────┐  │
│  │   Tauri App (frontend)   │  │  FastAPI Server  │  │
│  │                          │  │  (background)    │  │
│  │  - Ventana flotante      │  │                  │  │
│  │  - System tray icon      │  │  - /api/chat     │  │
│  │  - Shortcut global       │◄─┤  - /api/sessions │  │
│  │  - Notificaciones        │  │  - /api/upload   │  │
│  │  - Input + voz           │  │  - /api/models   │  │
│  └──────────────────────────┘  └───────┬──────────┘  │
│                                        │              │
│                               ┌────────┴──────────┐  │
│                               │    Ollama (LLM)    │  │
│                               │  (background)      │  │
│                               └────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Nuevo endpoint:** `/api/models` → devuelve modelos disponibles y permite cambiar.

---

## 3. Interfaz completa

```
 ┌─────────────────────────────────────────────────────┐
 │  ←  💬 Chat 1          💬 Chat 2       ＋          │  ← BARRA DE SESIONES
 │  ═══════════════════════════════════════════════════ │
 │                                                     │
 │  🧠 Qwen2.5:7b  ▼  🌐 Ollama  ▼    ⚡ Nivel 3  ▼  │  ← BARRA RÁPIDA
 │                                                     │
 │  ┌─────────────────────────────────────────────────┐│
 │  │  🤖 Hola Xavier, ¿en qué te ayudo?              ││
 │  │                                                 ││
 │  │  Tú: Dame el estado de los pagos               ││
 │  │  🤖 Revisando...                                ││
 │  │     🔧 Buscando Excel de pagos                 ││
 │  │     🔧 Procesando datos                        ││
 │  │  🤖 Aquí está el resumen:                      ││
 │  │     • Luz: pagado ✅                           ││
 │  │     • Internet: pendiente ⏳                   ││
 │  │     • Próximo: 25 jul                          ││
 │  │                                                 ││
 │  │  Tú: Envíame el reporte a mi WhatsApp           ││
 │  │  🤖 [Confirmar?] ¿Enviar a Xavier?              ││
 │  │     [✓ Sí]  [✗ No]                            ││
 │  └─────────────────────────────────────────────────┘│
 │                                                     │
 │  ┌───────────────────────────────────────────────┐  │
 │  │  Escribe un mensaje...       🎤  📎  🔍  ➤  │  │
 │  └───────────────────────────────────────────────┘  │
 └─────────────────────────────────────────────────────┘
```

### 3.1 Barra de sesiones (arriba)

```text
←  💬 Chat 1          💬 Chat 2       ＋
```

- **Chat 1, Chat 2** = sesiones activas, como tabs en el navegador
- **←** = volver a sesión anterior
- **＋** = nueva sesión al instante
- **Click en chat** = cambiar de sesión
- **Cada sesión tiene su propio historial y contexto**

Al hacer clic en ＋:

```
┌─────────────────────────────┐
│  Nueva sesión               │
│                             │
│  Nombre: [Trámites legales] │
│                             │
│  Especialidad:              │
│  ○ Asistente personal       │
│  ● Legal laboral            │
│  ○ BarOS                    │
│                             │
│  [Crear]  [Cancelar]        │
└─────────────────────────────┘
```

### 3.2 Barra rápida de modelo (abajo del header)

```text
🧠 Qwen2.5:7b  ▼  🌐 Ollama  ▼    ⚡ Nivel 3  ▼
```

Cada elemento es un **dropdown inmediato**. No abres preferencias — cambias desde aquí:

**Dropdown del modelo:**
```
┌─────────────────────────────────┐
│  🧠 Qwen2.5:7b                  │ ← seleccionado
│  🧠 Qwen2.5:1.5b                │
│  🧠 llama3.2:3b                 │
│  🧠 deepseek-coder:6.7b         │
│  ─────────────────────          │
│  📥 Descargar modelo nuevo...   │ ← abre selector
└─────────────────────────────────┘
```

**Dropdown del proveedor:**
```
┌─────────────────────────────────┐
│  🌐 Ollama (local)              │ ← seleccionado
│  ☁️ OpenAI (GPT-4o)            │
│  ☁️ Anthropic (Claude)         │
│  🔀 OpenRouter                  │
└─────────────────────────────────┘
```

**Al cambiar de proveedor/modelo:**
```text
✓ Modelo cambiado a GPT-4o
  La sesión actual sigue igual.
  Las nuevas respuestas usarán el nuevo modelo.
```

Sin reiniciar. Sin recargar. Inmediato.

### 3.3 Indicador de tools en uso

Cuando el agente está ejecutando herramientas, se ve en vivo:

```text
🤖 Revisando pagos...
   🔧 Herramientas en uso:         ← expandible
   ├── 📄 read_file("pagos.xlsx")  → ✅ 0.3s
   ├── 🗄️ query_db("SELECT...")   → ✅ 0.1s
   └── 📊 analyze(pagos)           → ⏳ procesando...
```

Así sabes exactamente qué está haciendo, sin magia.

---

## 4. Atajos de teclado

```text
⌘Space         → Abrir/ocultar ventana
⌘N             → Nueva sesión
⇧⌘N            → Nueva sesión con selector de especialidad
⌘T             → Cambiar entre sesiones (como tabs)
⌘W             → Cerrar ventana (sigue en background)
⌘M             → Cambiar modelo (abre dropdown)
⇧⌘M            → Ciclar al siguiente modelo
⌘,             → Preferencias
⌘↑             → Subir archivo / drag & drop
⌘Enter         → Enviar mensaje
⌘K             → Paleta de comandos (como VS Code)
Esc            → Cerrar ventana / cancelar
```

**⌘K — Paleta de comandos:**
```
┌─────────────────────────────────────┐
│  >                                │
│                                     │
│  📱 Nueva sesión                    │
│  🧠 Cambiar modelo a GPT-4o        │
│  🔄 Reiniciar sesión               │
│  📂 Abrir carpeta de documentos     │
│  ⚙️ Preferencias                    │
│  📋 Ver auditoría                   │
│  📤 Exportar conversación           │
└─────────────────────────────────────┘
```

---

## 5. Icono en la barra de menú

```
  ╔══════════════════════════════════════════════╗
  ║  ...  wifi  batería  🤖 R2    17:30   ║
  ╚══════════════════════════════════════════════╝
                         │
             Click →     ▼
              ┌─────────────────────────────────┐
              │  🤖 R2 Autonomous (3 sesiones)  │
              │  ─────────────────────          │
              │  💬 Chat 1 — Trámites          │
              │  💬 Chat 2 — Consulta rápida   │
              │  💬 Chat 3 — BarOS             │
              │  ─────────────────────          │
              │  ⌘N  Nueva sesión              │
              │  ─────────────────────          │
              │  📶 Ollama (Qwen2.5:7b)        │
              │  ⚡ Nivel 3                     │
              │  ─────────────────────          │
              │  ⚙️ Preferencias               │
              │  🚪 Salir                       │
              └─────────────────────────────────┘
```

---

## 6. Funcionalidades clave

### 6.1 Chat conversacional
- Burbujas como WhatsApp
- Indicador de escritura
- Tool calls visibles (expandir/colapsar)
- Markdown renderizado (código, tablas, lists)

### 6.2 Voz (después)
- 🎤 Speech-to-text local (Whisper)
- 🔊 TTS local
- Modo manos libres

### 6.3 Drag & drop de archivos
```text
Arrastras un PDF → el agente lo lee y dice:
"Recibí el contrato. ¿Quieres que lo analice?"
```

### 6.4 Multi-sesión
- Tabs como navegador
- Cada sesión con su contexto
- Persistencia al cerrar/reabrir app
- Sesiones compartidas entre web y WhatsApp

### 6.5 Notificaciones nativas
```text
Tarea larga completada → 🔔 en la barra
"La demanda está lista. ¿La revisamos?"
```

### 6.6 Modo compacto
```text
⌘R → Reduce la ventana a solo la barra de input
     Perfecto cuando solo quieres preguntar algo rápido
     Sin distracciones del historial
```

---

## 7. Preferencias

Separado de la barra rápida — esto es para configuración permanente.

### Ventana de preferencias:

```
┌─────────────────────────────────────────────────────┐
│  ⚙️ Preferencias                     ─  ☐  ✕      │
├─────────────────────────────────────────────────────┤
│  🧠 Modelo y API keys                               │
│  ┌─────────────────────────────────────────────┐   │
│  │ Proveedor: [Ollama ▼]                      │   │
│  │ Modelo:    [qwen2.5:7b ▼]                 │   │
│  │                                              │   │
│  │ ─── Solo si usas API cloud ───              │   │
│  │                                              │   │
│  │ 🔑 API Key                                   │   │
│  │ ┌─────────────────────────────────────────┐ │   │
│  │ │ sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx   │ │   │
│  │ └─────────────────────────────────────────┘ │   │
│  │ 📋 [Probar conexión]   ❌ No conectado    │   │
│  │                                              │   │
│  │ 💡 ¿Dónde conseguir API key?                │   │
│  │    platform.openai.com/api-keys             │   │
│  │                                              │   │
│  │ 🔒 Guardada en Keychain de macOS            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  📱 Canales                                        │
│  ┌─────────────────────────────────────────────┐   │
│  │ 📱 WhatsApp: [Conectado] [Desconectar]      │   │
│  │ 🤖 Telegram: [Añadir bot token...]          │   │
│  │    ┌─────────────────────────────────────┐ │   │
│  │    │ 123456:ABCdefGHIjklMNO             │ │   │
│  │    └─────────────────────────────────────┘ │   │
│  │    [Probar]                              │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  🔐 Seguridad                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ Nivel por defecto: [3 - Autónomo ▼]        │   │
│  │ Carpetas permitidas:                        │   │
│  │ 📁 ~/Trantor/DiscoE/     [✕]              │   │
│  │ 📁 ~/Documents/R2/       [✕]              │   │
│  │ [+ Agregar carpeta]                       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  🎤 Voz                                            │
│  ┌─────────────────────────────────────────────┐   │
│  │ ☐ Entrada por voz (Whisper)                │   │
│  │ ☐ Respuesta por voz                         │   │
│  │ Idioma: [Español ▼]                        │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  📢 Notificaciones                                  │
│  ┌─────────────────────────────────────────────┐   │
│  │ ☐ Notificar tareas completadas              │   │
│  │ ☐ Sonido al recibir respuesta               │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [Restaurar defaults]    [Guardar y cerrar]        │
└─────────────────────────────────────────────────────┘
```

**Flujo de API key:**
1. Usuario selecciona proveedor cloud (OpenAI, Anthropic, OpenRouter)
2. Aparece el campo 🔑 API Key
3. Pega la key
4. Click [Probar conexión] → valida que funciona
5. Se guarda en el Keychain del sistema (no en texto plano)
6. Puede cambiarla o quitarla cuando quiera
7. Si vuelve a Ollama local, la key queda guardada pero inactiva

---

## 8. Stack técnico

```text
Frontend (Tauri):
  - Tauri 2.x (Rust shell)         → App nativa
  - React + TypeScript              → UI
  - Tailwind CSS                    → Estilos
  - Lucide React                    → Iconos

Backend (FastAPI):
  - FastAPI                         → API server
  - Ollama Python client            → LLM
  - SQLite (local)                  → Memoria
  - whatasapp-web.js                 → Canales

Comunicación:
  - Tauri command system            → Llamadas al sistema nativo
  - HTTP (localhost) → API          → Datos del chat
  - WebSocket → streaming           → Respuestas en vivo
```

---

## 9. Logos e iconos

```text
App Icon:
  🤖 R2 (estilizado, en la barra de menú)

Splash:
  Logo R2 + "R2 Autonomous"
  "Tu agente personal. 100% local."
```

---

## 10. Distribución

```text
📦 R2 Autonomous.app

  • App bundle para macOS (.dmg)
  • Instalador para Windows (.msi)
  • AppImage para Linux (.AppImage)

  Todo con un solo comando:
  cargo tauri build
```

---

## 11. Checklist para Trantor

### App principal
- [ ] Proyecto Tauri + React
- [ ] System tray icon + menú con sesiones
- [ ] Shortcut global (Cmd+Space)
- [ ] Ventana flotante de chat

### Sesiones
- [ ] Barra de sesiones (tabs)
- [ ] Nueva sesión con selector de especialidad
- [ ] Persistencia de sesiones entre reinicios
- [ ] Atajo ⌘N, ⇧⌘N, ⌘T

### Cambio rápido de modelo
- [ ] Barra rápida con dropdowns
- [ ] Lista de modelos disponibles (desde Ollama API)
- [ ] Cambio de proveedor (Ollama ↔ OpenAI etc.)
- [ ] Descarga de modelo nuevo desde la UI
- [ ] Atajo ⌘M, ⇧⌘M

### Controles
- [ ] Input de texto + enviar
- [ ] Conexión FastAPI backend
- [ ] WebSocket streaming de respuestas
- [ ] Drag & drop archivos
- [ ] Tool calls visibles
- [ ] Paleta de comandos (⌘K)
- [ ] Preferencias
- [ ] Notificaciones nativas
- [ ] Build distribución
