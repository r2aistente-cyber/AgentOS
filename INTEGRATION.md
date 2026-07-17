# 🔌 R2 Autonomous — Integración con otros softwares

> **Versión:** 1.0
> **Propósito:** Cómo cualquier app (POS, web, mobile) se conecta a R2.

---

## 1. Filosofía

R2 no es una app aislada. Es un **servicio** al que todo tu ecosistema se conecta.

```text
Así NO:                        Así SÍ:

┌──────────┐                   ┌─────────────────────┐
│ R2 App   │                   │  R2 Autonomous      │
│ (solo)   │                   │  (servicio interno) │
└──────────┘                   └────┬────┬────┬──────┘
                                    │    │    │
                               ┌────┘    │    └────┐
                               ▼         ▼         ▼
                          ┌────────┐ ┌────────┐ ┌────────┐
                          │ BarOS  │ │ Web    │ │ Otra   │
                          │ (POS)  │ │ (app)  │ │ app    │
                          └────────┘ └────────┘ └────────┘
```

---

## 2. Modos de integración

### 2.1 API directa (cualquier software)

Cualquier app puede hablar con R2 con una simple llamada HTTP:

```python
import requests

# Desde BarOS, desde una web, desde una app mobile...
response = requests.post("http://localhost:8234/api/v1/chat", json={
    "session_id": "pos-session-123",
    "message": "¿Cuántas ventas llevamos hoy?",
    "user_id": "cajero1",
    "specialty": "baros",
    "context": {                           # ← contexto extra que R2 necesita
        "store_id": 42,
        "date": "2026-07-16"
    }
})

print(response.json()["reply"])
# → "Llevas 28 ventas por $1,234,500. 
#    El producto más vendido es aguardiente."
```

**Esto significa:** cualquier app tuya (POS, web, mobile) puede tener un botón "Preguntar a R2" y funciona con 3 líneas de código. Sin instalar nada más que el servidor de R2.

### 2.2 Widget de chat embebido (para web)

Un componente React que cualquiera de tus webs puede importar:

```tsx
// En BarOS, en la web de Legal, en cualquier lado
import { R2ChatWidget } from "@r2aistente/widget";

function POS() {
    return (
        <div>
            <POSUI />
            <R2ChatWidget              // ← botón flotante como Intercom
                position="bottom-right"
                server="http://localhost:8234"
                userId="cajero1"
                specialty="baros"
                context={{ store_id: 42 }}
            />
        </div>
    );
}
```

Se ve así en la pantalla del POS:

```
┌──────────────────────────────────────┐
│  POS - BarOS                         │
│                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐         │
│  │ Mesa1│ │ Mesa2│ │ Mesa3│    🤖  │  ← botón flotante
│  │ $120 │ │ $85  │ │ $200 │         │
│  └──────┘ └──────┘ └──────┘         │
│                                      │
│            ┌──────────────┐          │
│            │ 🤖 ¿En qué   │          │ ← panel abierto
│            │    puedo     │          │
│            │    ayudarte? │          │
│            │              │          │
│            │ Cajero:      │          │
│            │ "¿cuántas    │          │
│            │  ventas hoy?"│          │
│            │              │          │
│            │ 🤖 28 ventas │          │
│            │ por $1,234,500│          │
│            └──────────────┘          │
└──────────────────────────────────────┘
```

### 2.3 Eventos entrantes (Webhooks)

El POS le puede avisar a R2 cuando pasan cosas, y R2 reacciona:

```python
# Desde BarOS, cuando ocurre un evento:
requests.post("http://localhost:8234/api/v1/events", json={
    "event": "sale_completed",
    "data": {
        "total": 234500,
        "items": ["aguardiente", "cerveza"],
        "payment": "efectivo"
    },
    "store_id": 42
})
```

R2 puede:
- Acumular datos para responder preguntas
- Detectar anomalías (ej: "llevas 3 devoluciones en 1 hora")
- Enviar alertas por WhatsApp (ej: "se acabó el aguardiente")

### 2.4 Tools externas (el POS como herramienta de R2)

El POS también puede **exponer herramientas** para que R2 las use:

```python
# BarOS registra sus propias herramientas en R2
requests.post("http://localhost:8234/api/v1/tools/register", json={
    "tools": [
        {
            "name": "get_daily_sales",
            "description": "Obtiene ventas del día actual",
            "parameters": {
                "store_id": {"type": "integer"}
            },
            "endpoint": "http://localhost:5001/api/sales/today"
        },
        {
            "name": "check_inventory",
            "description": "Verifica stock de un producto",
            "parameters": {
                "product": {"type": "string"}
            },
            "endpoint": "http://localhost:5001/api/inventory/check"
        }
    ]
})
```

Así cuando el cajero pregunta "¿cuánto aguardiente queda?", R2:
1. Recibe el mensaje
2. Decide usar la herramienta `check_inventory`
3. La ejecuta → llama al endpoint del POS
4. Devuelve la respuesta al cajero

**Sin modificar el código de R2.** El POS solo registra sus tools y R2 las usa.

---

## 3. Flujo completo (BarOS + R2)

```text
CAJERO en el POS:
  "Oye R2, ¿cuántas ventas vamos hoy?"
       │
       ▼
┌─────────────────────────────┐
│  POST /api/v1/chat          │
│  { specialty: "baros",      │
│    message: "¿ventas hoy?" }│
└────────────┬────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  R2 recibe el mensaje       │
│  Especialidad BarOS:        │
│  "Eres un bartender..."     │
│                             │
│  Tools disponibles:         │
│  - get_daily_sales ← del POS│
│  - check_inventory ← del POS│
│  - read_file        ← base  │
│  - send_whatsapp    ← base  │
└────────────┬────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  R2 llama: get_daily_sales  │
│  → POST al endpoint del POS│
│  → POS responde:            │
│    { total: 1234500,        │
│      count: 28 }            │
└────────────┬────────────────┘
       │
       ▼
┌─────────────────────────────┐
│  R2 responde al cajero:     │
│  "Llevas 28 ventas por      │
│   $1,234,500. ¿Necesitas    │
│   algo más?"                │
└─────────────────────────────┘
```

---

## 4. Configuración de integraciones

Desde la UI de R2:

```
⚙️ Preferencias → Integraciones

┌─────────────────────────────────────────────┐
│  🔌 Integraciones                           │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🧾 BarOS                           │ ✅ │
│  │  http://localhost:5001              │    │
│  │  Tools registradas: 4               │    │
│  │  Eventos conectados: ✓              │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  🌐 Mi web (landing)               │    │
│  │  Widget: <script> embedido        │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  📱 App mobile                      │    │
│  │  API key: sk-r2-abc123             │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [+ Agregar integración]                    │
└─────────────────────────────────────────────┘
```

---

## 5. Nuevos endpoints para integración

```yaml
# API de integración

POST /api/v1/chat
  → Ya existe. El entry point universal.

POST /api/v1/tools/register
  → Registrar herramientas externas (desde el POS, etc.)
  Body: { name, description, parameters, endpoint }
  Response: { tool_id, status }

POST /api/v1/tools/unregister/{tool_id}
  → Quitar herramienta externa

GET /api/v1/tools/external
  → Listar herramientas registradas por integraciones

POST /api/v1/events
  → Recibir eventos externos
  Body: { event, data, source }
  Response: { received, actions_triggered }

GET /api/v1/widget.js
  → Script del widget embebido para webs
```

---

## 6. Seguridad en integraciones

```yaml
integrations:
  baros:
    url: http://localhost:5001
    api_key: sk-baros-local-...     # El POS se autentica con R2
    allowed_tools: [                 # Qué tools del POS puede usar R2
      get_daily_sales,
      check_inventory
    ]
    allowed_events: [                # Qué eventos recibe R2
      sale_completed,
      inventory_low
    ]
```

---

## 7. Resumen

```text
Cualquier software tuyo puede CONECTARSE a R2 de 3 formas:

1️⃣ API directa
   → POST /api/v1/chat desde cualquier lenguaje
   → 3 líneas de código y ya habla con R2

2️⃣ Widget embebido
   → <R2ChatWidget /> en React
   → <script> en HTML plano
   → Como Intercom/Drift pero local

3️⃣ Tools externas
   → El POS registra sus propias herramientas
   → R2 las usa sin modificar su código
   → Ej: BarOS expone get_daily_sales, check_inventory
```

---

## 8. Checklist para Trantor

- [ ] Endpoint `POST /api/v1/tools/register` (tools externas)
- [ ] Endpoint `POST /api/v1/events` (eventos entrantes)
- [ ] Widget React `<R2ChatWidget />`
- [ ] Widget script plano `<script src="/api/v1/widget.js">`
- [ ] Autenticación entre servicios (API keys por integración)
- [ ] Demo: BarOS conectado a R2
