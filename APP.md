# 🦀 R2 Autonomous — Desktop App Concept (Tauri)

> **Versión:** 1.0
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
│  │  - Input + voz           │  │                  │  │
│  └──────────────────────────┘  └───────┬──────────┘  │
│                                        │              │
│                               ┌────────┴──────────┐  │
│                               │    Ollama (LLM)    │  │
│                               │  (background)      │  │
│                               └────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**El backend (FastAPI) arranca con la máquina.** La app de escritorio solo es la interfaz. Así cuando abres la ventana, el agente ya está vivo.

---

## 3. Interfaz

### 3.1 Icono en la barra de menú

```
  ╔══════════════════════════════════════════════╗
  ║  ...  wifi  batería  🤖 R2    17:30   ║
  ╚══════════════════════════════════════════════╝
                         │
             Click →     ▼
              ┌─────────────────────────────┐
              │  🤖 R2 Autonomous           │
              │  ⌘ Nuevo chat               │
              │  ─────────────────────      │
              │  📶 Conectado (Ollama local) │
              │  ⚡ Activo                   │
              │  ─────────────────────      │
              │  ⚙️ Preferencias            │
              │  🚪 Salir                   │
              └─────────────────────────────┘
```

### 3.2 Ventana principal (al hacer click en "Nuevo chat" o ⌘Space)

```
 ┌─────────────────────────────────────────────┐
 │  🤖 R2 Autonomous                     🗑️ ⚙️ │
 ├─────────────────────────────────────────────┤
 │                                             │
 │  🤖 Hola Xavier, ¿en qué te ayudo?         │
 │                                             │
 │  Tú: Dame el estado de los pagos           │
 │  🤖 Revisando...                           │
 │     → Buscando Excel de pagos             │
 │     → Procesando datos                     │
 │  🤖 Aquí está el resumen:                  │
 │     • Luz: pagado ✅                       │
 │     • Internet: pendiente ⏳               │
 │     • Próximo: 25 jul                      │
 │                                             │
 │  Tú: Envíame el reporte a mi WhatsApp      │
 │  🤖 [Confirmar?] ¿Enviar a Xavier?         │
 │     [Sí]  [No]                             │
 │                                             │
 │  ┌───────────────────────────────────────┐ │
 │  │  Escribe un mensaje...    🎤  📎  ➤  │ │
 │  └───────────────────────────────────────┘ │
 └─────────────────────────────────────────────┘
```

### 3.3 Atajos de teclado

```text
⌘Space         → Abrir/ocultar ventana
⌘N             → Nuevo chat
⌘W             → Cerrar ventana (sigue en background)
⌘,             → Preferencias
⌘↑             → Subir archivo
⌘Enter         → Enviar mensaje
Esc            → Cerrar ventana
```

---

## 4. Funcionalidades clave

### 4.1 Chat conversacional

- Como WhatsApp/Telegram, pero nativo
- Mensajes con burbujas
- Indicador de escritura cuando el agente piensa
- Tool calls visibles (saber qué está haciendo)

### 4.2 Voz (opcional, después)

- 🎤 Botón para hablar (speech-to-text local con Whisper)
- 🔊 Respuesta por voz (TTS local)
- Modo manos libres

### 4.3 Drag & drop de archivos

```
Arrastras un PDF a la ventana
→ El agente lo lee automáticamente
→ "Acabo de recibir el contrato de Juan Pérez.
   ¿Quieres que lo revise?"
```

### 4.4 Multi-chat (tabs/sesiones)

- Varias conversaciones abiertas simultáneamente
- Cada una con su contexto
- Persistencia al cerrar/reabrir

### 4.5 Notificaciones nativas

```
Cuando el agente termina una tarea larga:
  🔔 Resultado listo
     "La demanda por despido injusto
      está generada. ¿La revisamos?"
```

---

## 5. Preferencias (ventana de configuración)

```
┌─────────────────────────────────────────────┐
│  ⚙️ Preferencias                    ─  ☐  ✕ │
├─────────────────────────────────────────────┤
│                                             │
│  🧠 Modelo                                  │
│  ┌─────────────────────────────────────┐    │
│  │ Proveedor: [Ollama ▼]              │    │
│  │ Modelo:    [qwen2.5:7b ▼]         │    │
│  │ Host:      [http://localhost:11434]│    │
│  └─────────────────────────────────────┘    │
│                                             │
│  🔐 Acceso                                  │
│  ┌─────────────────────────────────────┐    │
│  │ Nivel: [Autónomo (Nivel 3) ▼]      │    │
│  │ Carpetas: [📁 ~/Trantor/DiscoE/   │    │
│  │           [📁 ~/Documents/R2/     │    │
│  │           [+ Agregar carpeta]     │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  🎤 Voz                                     │
│  ┌─────────────────────────────────────┐    │
│  │ ☐ Habilitar entrada por voz         │    │
│  │ ☐ Respuesta por voz                 │    │
│  │ Idioma: [Español ▼]                 │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  📢 Notificaciones                          │
│  ┌─────────────────────────────────────┐    │
│  │ ☐ Notificar tareas completadas      │    │
│  │ ☐ Sonido al recibir respuesta       │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

---

## 6. Stack técnico

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

## 7. Logos e iconos

```text
App Icon:
  🤖 R2 (estilizado, en la barra de menú)

Splash:
  Logo R2 + "R2 Autonomous"
  "Tu agente personal. 100% local."
```

---

## 8. Distribución

```text
📦 R2 Autonomous.app

  • App bundle para macOS (.dmg)
  • Instalador para Windows (.msi)
  • AppImage para Linux (.AppImage)

  Todo con un solo comando:
  cargo tauri build
```

---

## 9. Checklist para Trantor

- [ ] Crear proyecto Tauri + React
- [ ] System tray icon + menú
- [ ] Ventana flotante (Chat)
- [ ] Shortcut global (Cmd+Space)
- [ ] Input de texto + enviar
- [ ] Conexión a FastAPI backend
- [ ] Stream de respuestas (WebSocket)
- [ ] Drag & drop archivos
- [ ] Preferencias (config)
- [ ] Notificaciones nativas
- [ ] Build para distribución
