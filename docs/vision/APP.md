# 🖥️ AgentOS — Desktop App (Tauri)

> **Versión:** 2.0  
> **Propósito:** App de escritorio nativa para gestionar agentes  
> **Framework:** Tauri 2.x + React + Rust

---

## 1. Filosofía

AgentOS no es un chat. Es el **administrador de tus agentes**.

Lo abres como cualquier programa en tu PC (`AgentOS.exe` / `AgentOS.app`). Ves el dashboard con tus agentes. Creas nuevos, los configuras, los inicias o los detienes. Todo en ventanas nativas.

> No es una página web. No necesitas Chrome. No escribes `localhost`.

---

## 2. Ventanas de AgentOS

### Ventana principal — Dashboard

```
┌────────────────────────────────────────────────────────┐
│ AgentOS                        — □ ×                   │
├────────────────────────────────────────────────────────┤
│ 🏠 Dashboard     [+ Crear Agente]                      │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🤖 R2 PRIME           🟢 Online    9001     ██░░  │ │
│ │  D:\Agentes\R2 PRIME\     Ollama · qwen2.5:7b    │ │
│ │  [Abrir] [Config] [Detener] [Logs]               │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ ⚖️ Abogado Laboral   🟢 Online    9002     █░░░  │ │
│ │  C:\Users\...\Bufete\   Ollama · qwen2.5:7b      │ │
│ │  [Abrir] [Config] [Detener] [Logs]               │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ 📢 Marketing Bot     🔴 Offline   9003             │ │
│ │  E:\Marketing\          OpenAI · gpt-4o            │ │
│ │  [Abrir] [Config] [▶️ Iniciar] [Logs]              │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│  CPU: 12%  ·  RAM: 1.2GB / 16GB  ·  Discos: 45%       │
└────────────────────────────────────────────────────────┘
```

### Ventana — Crear Agente (Wizard)

```
┌────────────────────────────────────────────────────────┐
│ ✨ Nuevo Agente ··· Paso 2 de 5         — □ ×          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  📁 Ubicación de instalación:                          │
│  [D:\Agentes\                         ] [📂 Examinar] │
│                                                        │
│  Nombre del agente: [R2 PRIME                       ] │
│  Descripción: [Asistente personal de Xavier         ] │
│                                                        │
│  ─────────────────────────────────────────────         │
│                                                        │
│  [← Atrás]                          [Siguiente →]      │
└────────────────────────────────────────────────────────┘
```

### Ventana — Config del agente

```
┌────────────────────────────────────────────────────────┐
│ ⚙️ R2 PRIME ··· Config           — □ ×                 │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Personalidad                                           │
│   Tono: [Directo ▼]  Humor: [Sarcástico ▼]           │
│   Trato: [Tutea ▼]    Empatía: [Leal ▼]              │
│                                                        │
│  LLM                                                    │
│   Proveedor: [Ollama ▼]     Modelo: [qwen2.5:7b ▼]   │
│   Temperatura: [████████░░░ 0.7]                      │
│   API Key: [····························] 🔒          │
│                                                        │
│  Tools                                                  │
│  ☑ read_file    ☑ write_file    ☑ list_files           │
│  ☑ search_web   ☑ fetch_url     ☑ save_memory          │
│  ☑ read_document ☑ read_image   ☐ exec_command         │
│                                                        │
│  Seguridad                                              │
│   Nivel: [● Nivel 2 — Lectura + escritura controlada] │
│   Sandbox: [D:\Agentes\R2 PRIME\data\           ]    │
│                                                        │
│  [Cancelar]  [Guardar]                                  │
└────────────────────────────────────────────────────────┘
```

### Ventana — Chat con el agente

```
┌────────────────────────────────────────────────────────┐
│ 💬 R2 PRIME                              — □ ×         │
├────────────────────────────────────────────────────────┤
│                                                        │
│  🤖 R2 PRIME: ¿En qué puedo ayudarte?                  │
│                                                        │
│  Tú: Necesito una carta laboral                        │
│  🤖: Claro, deme los datos del empleado                │
│      y el salario actual.                              │
│                                                        │
│  Tú: [Adjunta: Juan Perez.docx]                        │
│  🤖: Veo los datos de Juan Pérez.                      │
│      Generando carta laboral...                         │
│                                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ 📎 Juan Perez.docx   🖼️ firma.png             │   │
│  └────────────────────────────────────────────────┘   │
│  [✏️ Escribe un mensaje...]                    [📎] ▶️ │
└────────────────────────────────────────────────────────┘
```

---

## 3. Comportamiento

| Acción | Comportamiento |
|--------|---------------|
| Abrir AgentOS | Ventana principal con dashboard |
| Cerrar ventana | Se minimiza a bandeja del sistema |
| Clic en "Crear Agente" | Nueva ventana independiente (wizard) |
| Clic en "Abrir" (agente) | Nueva ventana con el chat del agente |
| Clic en "Config" | Ventana de configuración del agente |
| Clic en "Detener" | Mata el proceso, libera puerto y RAM |
| Inicio del sistema | AgentOS arranca como servicio, inicia agentes con auto_restart |
| Click derecho en bandeja | Menú rápido: "Abrir AgentOS" / "Iniciar todos" / "Salir" |

---

## 4. Tecnología

```text
┌──────────────────────────────────────────────────────┐
│  AgentOS.exe / AgentOS.app                           │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Tauri (Rust shell)                            │  │
│  │  • Ventanas nativas del SO                     │  │
│  │  • Sin Electron (liviano, ~5MB)                │  │
│  │  • Icono en bandeja del sistema                │  │
│  │  • Atajos globales (Cmd+Space)                 │  │
│  │  • Arranque automático al iniciar sesión        │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  React (UI)                                    │  │
│  │  • Interfaz renderizada por Tauri              │  │
│  │  • Se ve nativa (no parece web)                │  │
│  │  • Componentes: Dashboard, Wizard, Config, Chat│  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Hub Engine (sidecar Python/FastAPI)           │  │
│  │  • Arranca con AgentOS                         │  │
│  │  • Gestiona los procesos de los agentes         │  │
│  │  • Se comunica con la UI por IPC/localhost      │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 5. Instalación desatendida

AgentOS se instala en `C:\AgentOS\` (o `~/AgentOS/` en Mac/Linux). Sin registry, sin dependencias externas más que Ollama (si se usa).

El instalador pregunta solo una cosa:
```
📁 ¿Dónde quieres que se creen los agentes por defecto?
   [D:\Agentes\    ] [📂 Examinar]
```
