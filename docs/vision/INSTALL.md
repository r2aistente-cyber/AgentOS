# 📦 AgentOS — Instalación

> **Versión:** 2.0  
> **Instalación:** App nativa, sin dependencias externas

---

## 1. La experiencia

```
⬇️ 1. Descargas AgentOS-Setup.exe (o .dmg / .AppImage)
▶️ 2. Doble clic, sigue el instalador
🚀 3. Se abre AgentOS
✨ 4. Creas tu primer agente y ¡listo!

Sin terminal. Sin comandos. Sin configuración manual.
```

---

## 2. Requisitos

| Componente | Mínimo | Recomendado |
|-----------|--------|-------------|
| **Sistema** | Windows 10+, macOS Ventura+, Linux | — |
| **RAM** | 4 GB | 8 GB+ |
| **Disco** | 500 MB (AgentOS) | + espacio según data de agentes |
| **Ollama** | Opcional (solo si usas modelos locales) | qwen2.5:7b (~4 GB) |

> Los agentes pueden usar OpenAI, Anthropic, etc. sin necesidad de Ollama.

---

## 3. Instalación paso a paso

### Windows

1. Descarga `AgentOS-2.0-Setup.exe`
2. Ejecuta el instalador
3. Elige la carpeta de instalación (default: `C:\AgentOS\`)
4. Elige la carpeta por defecto para nuevos agentes (default: `C:\AgentOS\agents\`)
5. ✅ Listo — AgentOS se abre automáticamente

### macOS

1. Descarga `AgentOS-2.0.dmg`
2. Arrastra AgentOS a Applications
3. Abre AgentOS (puede pedir permisos de accesibilidad para bandeja)
4. En el primer inicio, configura la carpeta de agentes

### Linux

1. Descarga `AgentOS-2.0.AppImage`
2. `chmod +x AgentOS-2.0.AppImage`
3. Ejecuta

---

## 4. Primer inicio

Al abrir AgentOS por primera vez:

```
┌────────────────────────────────────────────────────────┐
│  🚀 Bienvenido a AgentOS                               │
│                                                        │
│  Antes de empezar, elige dónde se guardarán            │
│  tus agentes por defecto. Puedes cambiarlo             │
│  después al crear cada agente.                         │
│                                                        │
│  📁 Carpeta de agentes:                                │
│  [D:\Agentes\                         ] [📂 Examinar] │
│                                                        │
│  [Omitir]                         [Continuar →]       │
└────────────────────────────────────────────────────────┘
```

Luego ves el dashboard vacío y el botón **"+ Crear tu primer agente"**.

---

## 5. Qué se instala

```
C:\AgentOS\
├── AgentOS.exe              ← La aplicación (Tauri shell)
├── hub-engine.exe           ← El backend (Python empaquetado con PyInstaller)
├── config.yaml              ← Configuración del Hub
├── templates\               ← Plantillas para crear agentes
│   ├── agent_main.py
│   ├── default_config.yaml
│   ├── llm\                 ← Código base del agente
│   ├── tools\
│   ├── security\
│   └── memory\
├── data\                    ← Datos del Hub (registro de agentes)
└── logs\                    ← Logs del Hub
```

Cada agente vive en la ubicación que el usuario eligió al crearlo, NO dentro de esta carpeta.
