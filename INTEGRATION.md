# 🔌 AgentOS — Integración con otros softwares

> **Versión:** 2.0  
> **Arquitectura:** Múltiples agentes, cada uno con su API

---

## 1. Filosofía

Cada agente en AgentOS es un **servicio** al que otras aplicaciones pueden conectarse.

No tienes un solo punto de integración. Tienes N APIs, una por agente. Cada una con su propia personalidad, tools y sandbox.

```text
                          ┌─────────────────────┐
                          │     AgentOS Hub      │
                          │   (solo gestión)     │
                          └─────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  🤖 R2 PRIME     │     │  ⚖️ Abogado       │     │  🧾 BarOS         │
│  Puerto 9001      │     │     Puerto 9002   │     │     Puerto 9003  │
│  ─────────       │     │     ─────────     │     │     ─────────    │
│  REST API        │     │     REST API      │     │     REST API     │
│  WebSocket       │     │     WebSocket     │     │     WebSocket    │
│  WhatsApp        │     │     Web           │     │     WhatsApp     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
   Otros softwares            Apps externas              POS / Clientes
```

---

## 2. Integración vía REST API

Cada agente expone su propia API REST en su puerto:

```yaml
POST /api/v1/chat
  → Enviar mensaje al agente
  Body: { session_id, message, user_id, files }
  Response: { reply, tools_used, attachments }

GET  /api/v1/sessions
  → Sesiones activas del agente

POST /api/v1/upload
  → Subir archivo al agente

GET  /api/v1/files
  → Archivos almacenados por el agente
```

Cualquier software (POS, web, app móvil) puede hablar con cualquier agente.

### 💥 Caso real: POS reemplazando su IA integrada por un agente

#### Situación actual
El POS-NeuralForge tiene una IA integrada directamente en su backend (OpenAI/Ollama wrapper). Esto crea acoplamiento: para cambiar la IA hay que modificar el POS, y la IA no tiene memoria, ni canales, ni herramientas extensibles.

#### Con AgentOS

Se crea un agente **BarOS** instalado dentro de la misma carpeta del POS:

```
C:\POS-NeuralForge\
├── backend\               ← El POS sigue igual
├── frontend\
├── database.sqlite         ← BD del POS
│
└── BarOS\                  ← Agente instalado AQUÍ
    ├── config.yaml
    ├── agent_main.py       ← Proxy que el POS llama por HTTP
    ├── tools\
    │   └── consultar_ventas.py  ← Lee la BD directo
    ├── memory.db
    └── data\
```

#### El POS elimina su IA integrada y llama al agente

```python
# 🚫 ANTES — IA acoplada al POS
# respuesta = openai.chat(...)  ← Esto se elimina

# ✅ DESPUÉS — El POS llama al agente
import requests

response = requests.post(
    "http://localhost:9003/api/v1/chat",
    json={
        "session_id": None,
        "message": "¿Cuánto aguardiente vendí ayer?",
        "user_id": "pos-cajero"
    },
    timeout=10
)

resultado = response.json()
print(resultado["reply"])
# → "Ayer vendiste 12 botellas de aguardiente.
#    Un 20% más que el jueves pasado."

# Los adjuntos también funcionan:
# files = {"file": open("reporte_diario.xlsx", "rb")}
# r = requests.post("http://localhost:9003/api/v1/chat", files=files, data={"message": "Analiza esto"})
```

#### La IA (BarOS) tiene tools que operan sobre el POS

```python
# C:\POS-NeuralForge\BarOS\tools\consultar_ventas.py
# Tool personalizada que lee directamente la BD del POS

@tool(name="consultar_ventas",
      description="Consulta las ventas del POS para una fecha")
def consultar_ventas(fecha: str = None) -> dict:
    db_path = "C:\\POS-NeuralForge\\database.sqlite"
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(total) FROM ventas WHERE date(fecha) = ?
    """, [fecha or "today"])
    total = cursor.fetchone()[0] or 0
    conn.close()
    return {"fecha": fecha, "total": total}
```

**El POS ni siquiera sabe qué herramientas tiene el agente. Solo le manda mensajes y recibe respuestas.**

#### Comparativa

| Antes (IA integrada) | Después (Agente BarOS) |
|---------------------|----------------------|
| IA acoplada al POS, tocarlo cuesta | Independiente, el POS solo hace HTTP |
| Sin memoria entre sesiones | Memory.db propia, recuerda todo |
| Tools limitadas al código del POS | Tools infinitas, solo crear un .py |
| Sin WhatsApp | Se activa en config.yaml y responde |
| Sin logs | Auditoría completa |
| Si la IA falla, el POS se cae | Si el agente falla, el POS sigue |
| Una sola personalidad | Personalidad configurable |

#### Código para embeber en el POS (JavaScript/Node)

```javascript
// POS-NeuralForge/backend/services/agentClient.js
const AGENT_URL = 'http://localhost:9003/api/v1/chat';

async function askAgent(message, sessionId = null) {
    const res = await fetch(AGENT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: sessionId,
            message: message,
            user_id: 'pos-cajero'
        })
    });
    return await res.json();
}

// Uso en cualquier parte del POS:
// const { reply } = await askAgent("Recomiéndame un producto");
```

¿Ventaja? El POS no necesita saber si BarOS usa Ollama, OpenAI, o lo que sea. Eso se configura desde AgentOS sin tocar una línea del POS.

---

## 3. Integración vía WebSocket

Para respuestas en tiempo real (streaming del LLM):

```
ws://localhost:{port}/api/v1/chat/stream
```

El agente envía tokens conforme el LLM los genera, en lugar de esperar la respuesta completa.

---

## 4. Integración por eventos (Webhooks)

Cada agente puede emitir eventos a URLs configuradas:

```yaml
# En config.yaml del agente
webhooks:
  on_message:
    - url: "http://mi-app.com/api/agent-log"
      events: ["message_sent", "tool_executed"]
  on_error:
    - url: "http://mi-monitor.com/alert"
      events: ["agent_crash", "tool_failed"]
```

---

## 5. Integración desde la app AgentOS

Desde AgentOS, el usuario ve y usa los agentes. Pero otros programas se conectan directamente al agente que les corresponde, sin pasar por AgentOS.

```
Agente BarOS  ←→  POS del bar
Agente Legal  ←→  Web app del bufete
R2 PRIME      ←→  Scripts de automatización de Xavier
```

Cada integración es independiente. Si el POS deja de funcionar, el bufete legal sigue andando.
