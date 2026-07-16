# 📦 R2 Autonomous — Instalación en 60 segundos

> **Problema:** OpenClaw requiere Node, npm, onboard, config de APIs, canales, daemon, skills...
> **Solución:** R2 Autonomous = doble clic y ya.

---

## 1. La experiencia ideal

```text
⬇️ 1. Descargas R2-Autonomous.dmg
▶️ 2. Arrastras a Applications
🚀 3. Abres R2
✅ 4. Ya puedes hablar

Sin terminal. Sin comandos. Sin configuración.
```

---

## 2. ¿Qué pasa en el primer inicio?

La app detecta que es la primera vez y ejecuta un **asistente de setup integrado** — no una terminal:

```
┌─────────────────────────────────────────────┐
│  🚀 Bienvenido a R2 Autonomous              │
│                                             │
│  Tu agente personal. 100% local.            │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  📦 Instalando componentes...         │  │
│  │                                       │  │
│  │  ✓ FastAPI server... listo            │  │
│  │  ✓ Ollama... descargando (2.1 GB)...  │  │
│  │  ████████░░░░░░░░░░ 45%              │  │
│  │                                       │  │
│  │  📥 Qwen2.5:7b... descargando         │  │
│  │  ██████░░░░░░░░░░░░ 30%              │  │
│  │                                       │  │
│  │  ⏱️ Aprox 3-5 minutos (según internet)│  │
│  └───────────────────────────────────────┘  │
│                                             │
│  [Cancelar]          [Continuar en fondo] ▶ │
└─────────────────────────────────────────────┘
```

---

## 3. Instalación técnica (lo que pasa detrás)

La app de Tauri contiene **todo** lo necesario:

```text
📦 R2 Autonomous.app/
├── R2 Autonomous (binario)          → La app en sí
├── backend/                          → FastAPI compilado (PyInstaller)
│   └── r2-server                     → Ejecutable standalone
├── ollama/                           → Ollama empaquetado
│   └── ollama-darwin                 → Binario para macOS
└── scripts/
    └── install.sh                    → Script de setup único
```

**No requiere:**

| ❌ No necesitas | Por qué |
|---|---|
| Node.js | FastAPI va empaquetado con PyInstaller |
| npm/pnpm | Nada de npm |
| Python | El server es un binario compilado |
| Docker | Ollama se instala automáticamente |
| APIs keys | LLM local, sin keys |
| Terminal | Nunca |

---

## 4. Lo único que requiere internet

```text
Primer inicio:
  ┌─────────────────────────────┐
  │  Descarga Ollama (~300 MB)  │
  │  Descarga modelo (~4 GB)    │
  │  → Una sola vez             │
  └─────────────────────────────┘

Después:
  ┌─────────────────────────────┐
  │  Nada. Todo local.          │
  │  Sin internet = funciona     │
  └─────────────────────────────┘
```

---

## 5. En segundo plano (siempre activo)

Cuando cierras la ventana de R2:

```text
⚙️ La app se minimiza a la barra de menú
⚙️ FastAPI server sigue corriendo
⚙️ Ollama sigue corriendo
⚙️ Puedes recibir respuestas
```

Cuando abres otra vez:

```text
⌘Space → Ventana aparece al instante
        → El agente ya está vivo
        → Sigue la conversación donde la dejaste
```

---

## 6. Cómo se instala Ollama automáticamente

```python
# backend/installer.py
# Esto corre UNA SOLA VEZ, en el primer inicio

import subprocess
import os
import requests

class Installer:
    def __init__(self, on_progress):
        self.on_progress = on_progress  # callback a la UI
    
    def install(self):
        # 1. Descargar Ollama si no existe
        if not self._ollama_installed():
            self.on_progress("Descargando Ollama...")
            url = "https://ollama.com/download/Ollama-darwin.zip"
            self._download_and_extract(url, "~/Applications/Ollama.app")
        
        # 2. Iniciar Ollama
        self.on_progress("Iniciando Ollama...")
        subprocess.run(["open", "-a", "Ollama"])
        
        # 3. Descargar modelo
        self.on_progress("Descargando modelo Qwen2.5:7b...")
        subprocess.run(["ollama", "pull", "qwen2.5:7b"])
        
        # 4. Iniciar servidor FastAPI
        self.on_progress("Iniciando R2 server...")
        subprocess.Popen(["./r2-server"])
        
        # 5. ¡Listo!
        self.on_progress("Completo. ¡Ya puedes hablar con R2!")
```

---

## 7. Instalación para empresas

```text
Para firmas de abogados, bares, etc.:

📦 USB de instalación:
  ├── R2 Autonomous.dmg
  ├── model_Qwen2.5_7b.gguf  (pre-descargado)
  └── install_offline.sh

→ Sin internet. Todo en el USB.
→ Doble clic en install_offline.sh
→ 2 minutos y listo.
```

---

## 8. Versiones

```text
R2.app → siempre actualizado

  • Auto-update (Tauri built-in)
  • Descarga nueva versión en background
  • Pide reiniciar cuando está lista

  Cliente no hace nada. La app sola se actualiza.
```

---

## 9. Comparativa con OpenClaw

| Paso | OpenClaw | R2 Autonomous |
|---|---|---|
| 1 | Instalar Node 24+ | ⬇️ Descargar R2.dmg |
| 2 | npm install -g openclaw | ▶️ Arrastrar a Applications |
| 3 | openclaw onboard | 🚀 Abrir app |
| 4 | Configurar APIs (OpenAI, etc.) | ⏳ Esperar descarga modelo |
| 5 | Configurar canales (WhatsApp, etc.) | ✅ Hablar con R2 |
| 6 | Configurar daemon (launchd) | — (built-in) |
| 7 | Skills, HEARTBEAT.md, standing orders | — (built-in) |
| | **~30-60 minutos** | **~1 minuto manual + 5 min descarga** |

---

## 10. Resumen

```text
⬇️ Descargas
▶️ Abre
✅ Habla

Esa es toda la instalación de R2 Autonomous.
Detrás, la app se encarga de todo:
  • Ollama
  • Modelo
  • Servidor
  • Actualizaciones
  • Persistencia

El usuario nunca ve una terminal.
Nunca instala Python, Node, npm, ni nada.
```

---

## 11. Checklist para Trantor

- [ ] Setup: Tauri bundle structure
- [ ] Backend compilado como binario standalone (PyInstaller)
- [ ] First-run wizard (UI + progreso)
- [ ] Descarga automática de Ollama
- [ ] Descarga automática de modelo
- [ ] Auto-update (Tauri)
- [ ] Modo offline USB
