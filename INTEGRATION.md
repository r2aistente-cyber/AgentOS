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

### Ejemplo: POS hablando con BarOS

```python
# Desde el POS (Python, Node, PHP, cualquier lenguaje)
response = requests.post(
    "http://localhost:9003/api/v1/chat",
    json={
        "session_id": None,
        "message": "¿Cuánto aguardiente vendí ayer?",
        "user_id": "cajero"
    }
)
print(response.json()["reply"])
# → "Ayer vendiste 12 botellas de aguardiente. 
#    Un 20% más que el jueves pasado."
```

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
