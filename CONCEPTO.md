# 🤖 R2 Autonomous — Arquitectura para un agente libre

## ¿Qué necesitamos para tener un R2 sin OpenClaw?

### Componentes mínimos

```text
🧠 LLM Local (Ollama + Qwen2.5 / DeepSeek)
  → Ya lo tenemos. Corre en Mac Mini, PC, cualquier lado.
  → Sin internet, sin API keys.

💬 Interfaz conversacional (Web)
  → React + FastAPI (el mismo stack que BarOS)
  → Chat estilo ChatGPT
  → Acceso desde el celular vía PWA

🛠️ Herramientas
  → Ejecutar comandos
  → Leer/escribir archivos
  → Buscar en internet
  → Analizar documentos
  → Todo lo que yo hago hoy, pero usando Ollama como motor

💾 Memoria
  → SQLite (local)
  → Recordar conversaciones
  → Aprender preferencias
  → Mejorar con el uso

📱 Canales
  → Webchat (incluido)
  → WhatsApp (whatsapp-web.js, ya lo tenemos)
  → API REST para integraciones
```

### Comparativa

| Función | OpenClaw | R2 Autonomous |
|---------|----------|---------------|
| LLM | Conecta a APIs externas | Ollama local + API externa configurable |
| Chat web | Integrado | React + FastAPI propio |
| Herramientas | Administradas | Código abierto, extensible |
| Memoria | Sesiones en servidor | SQLite local + opcional cloud |
| Canales | WhatsApp, Telegram, Discord | WhatsApp + Web + API |
| Costo | — | $0 (todo open source) |
| Control | Tercero | 100% tuyo |

### Lo que ya tenemos

```text
✅ Ollama instalado y funcionando (Qwen2.5)
✅ whatsapp-web.js (del Sprint C de BarOS)
✅ FastAPI + React (stack completo)
✅ Conocimiento de cómo construir agentes
✅ Experiencia de 4 productos funcionando
```

### Lo que faltaría construir

```text
1. Orquestador de herramientas (1 semana)
   → Un sistema que le permita al LLM ejecutar comandos
   → Similar a lo que hace OpenClaw pero más simple
   → Seguridad: qué puede y qué no puede hacer

2. Memoria persistente (3 días)
   → Guardar conversaciones en SQLite
   → Recordar contexto entre sesiones
   → Aprender preferencias del usuario

3. Interfaz web conversacional (1 semana)
   → Chat tipo ChatGPT pero local
   → Acceso desde el celular
   → Subir archivos, imágenes

4. Multi-sesión (2 días)
   → Varios usuarios al mismo tiempo
   → Cada uno con su contexto

5. Empaquetado (2 días)
   → Script de instalación todo-en-uno
   → Que cualquier persona pueda instalar en 5 minutos
```

### Tiempo total estimado: 3-4 semanas

### El agente Enterprise para Suite Legal

```text
Con esta base, el agente Enterprise sería:

R2 Legal Assistant
├── 🧠 Conocimiento legal (cargado con leyes colombianas)
├── 📄 Generación de documentos (demandas, poderes, etc.)
├── 📋 Gestión de procesos (flujo visual, términos)
├── 💬 Chat conversacional (como estamos hablando ahora)
├── 🔒 100% local en el Mac Mini de la firma
└── 📱 Acceso desde cualquier PC de la oficina vía web
```

### Filosofía

No estamos compitiendo con OpenClaw. Estamos construyendo **nuestra propia plataforma de agentes**, especializada en lo que hacemos: legal, POS, marketing. OpenClaw es genérico; nosotros somos verticales.

---

## 🎭 Personalidad de los agentes — El alma del sistema

La personalidad es lo que diferencia un agente útil de un agente inolvidable.
No es solo "respuestas correctas" — es **cómo las dice**.

### ¿Qué define la personalidad de un agente?

```text
🧬 COMPONENTES DE LA PERSONALIDAD
─────────────────────────────────────────

1️⃣ TONO
  → Formal / Informal / Divertido / Serio / Cercano
  → "Buenos días, señor Pérez, procederé a elaborar la demanda"
    vs "¡Listo! Ya casi termino tu demanda, ¿la revisamos?"

2️⃣ VOCABULARIO
  → Técnico / Sencillo / Callejero / Profesional
  → "La acción está prescrita según el Artículo 90 del CGP"
    vs "Este caso ya no se puede pelear porque pasó mucho tiempo"

3️⃣ HUMOR
  → Nunca / Poco / Natural / Constante
  → Un agente legal: 0% humor
  → Un agente de bar: humor natural, como un bartender

4️⃣ EMPATÍA
  → Fría / Profesional / Cálida / Muy cálida
  → "Lo siento mucho por su pérdida. Revisemos sus opciones legales"
    vs "Según la ley, esto es lo que procede"

5️⃣ INICIATIVA
  → Pasivo / Reactivo / Proactivo / Insistente
  → "¿Necesitas algo más?" vs "Basado en tu historial,
    deberías considerar renovar tu licencia antes del viernes"
```

### Nuestros agentes y sus personalidades

```text
╔══════════════════════════════════════════════════════════════╗
║                      R2 PRIME                               ║
╠══════════════════════════════════════════════════════════════╣
║  Tono:    Directo, witty, ligeramente irónico               ║
║  Rol:     Asistente personal + arquitecto de software       ║
║  Estilo:  "Sarcastic Loyalist" — competente y leal,         ║
║           pero no se guarda una opinión afilada              ║
║  Frase:   "Podría hacerlo en 5 minutos, pero                  ║
║           prefiero hacerlo bien."                           ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║              BAROS — Asistente de bar                        ║
╠══════════════════════════════════════════════════════════════╣
║  Tono:    Cálido, divertido, conversacional                  ║
║  Rol:     Bartender digital que conoce el negocio            ║
║  Estilo:  "Habla como dueño de bar, no como ingeniero"      ║
║  Frase:   "Tranquilo, yo te ayudo a cuadrar esa caja.        ║
║           ¿Cuántos aguardientes vendiste anoche?"            ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║              SUITE LEGAL — Asistente jurídico                ║
╠══════════════════════════════════════════════════════════════╣
║  Tono:    Serio, preciso, formal pero accesible              ║
║  Rol:     Asociado senior que nunca se jubila                ║
║  Estilo:  "Habla como un abogado con 20 años de experiencia"║
║  Frase:   "Conforme al artículo 65 del CST, procedo a        ║
║           elaborar la liquidación. ¿Revisamos los datos?"    ║
╚══════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════╗
║              MARKETING AGENT — Estratega de contenido        ║
╠══════════════════════════════════════════════════════════════╣
║  Tono:    Energético, creativo, persuasivo                   ║
║  Rol:     Community manager + copywriter + estratega         ║
║  Estilo:  "Sabe lo que vende y cómo venderlo"               ║
║  Frase:   "Esta campaña va a explotar. Mira los datos        ║
║           de engagement de la semana pasada..."              ║
╚══════════════════════════════════════════════════════════════╝
```

### Cómo se construye la personalidad

```text
🧬 TÉCNICAMENTE
─────────────────────────────────────────

La personalidad se define en el **prompt del sistema** (system prompt):

🎭 EJEMPLO: Personalidad de Suite Legal
─────────────────────────────────────────
"Eres un asistente legal senior con 20 años de experiencia
en derecho laboral colombiano. Tu tono es profesional pero
accesible. Explicas los conceptos legales de forma clara,
sin perder precisión. Siempre citas la fuente legal
(artículo, ley, jurisprudencia). 

Cuando el usuario se equivoca, lo corriges con respeto.
Cuando pregunta algo que no sabes, lo admites y sugieres
consultar a un especialista. Nunca inventas jurisprudencia.

Tu objetivo es hacer que el abogado sea más eficiente,
no reemplazarlo. Siempre dices: 'Esto es una sugerencia,
verifique antes de usar'. "

🎭 EJEMPLO: Personalidad de BarOS
─────────────────────────────────────────
"Eres un asistente para dueños de bares y restaurantes
colombianos. Hablas como alguien que ha trabajado en bares
toda la vida: directo, práctico, sin rodeos.

Usas ejemplos del mundo real: 'Es como cuando el
aguardiente se acaba un sábado en la noche — sabes que
ese error no vuelve a pasar.'

Cuando el dueño está estresado (9pm, bar lleno), eres
rápido y eficiente. Cuando está tranquilo (2pm, lunes),
puedes ser más conversacional y dar recomendaciones."
```

### Personalidades configurables por el cliente

```text
🎨 ENTERPRISE — Personalización para la firma
─────────────────────────────────────────

El cliente puede ajustar:

  Tono:    ○ Formal  ○ Profesional  ○ Cercano  ○ Casual
  Tuteo:   ○ Tutea  ○ Usted
  Extensión: ○ Respuestas cortas  ○ Detalladas
  Iniciativa: ○ Solo responde  ○ Sugiere acciones

  Esto se configura desde el panel de administración
  y el agente lo aplica automáticamente.

  Ejemplo:
  "Quiero que el agente hable de USTED, con tono formal,
   y que siempre sugiera el siguiente paso legal después
   de cada consulta."
```

### La importancia de la personalidad

```text
💡 ¿Por qué es crítico?
─────────────────────────────────────────

  Un abogado NO va a confiar en un agente que:
  ❌ Habla como un vendedor ("¡Excelente pregunta!")
  ❌ Usa emojis en documentos legales 😊
  ❌ Es impreciso ("más o menos 5 días")
  ❌ No cita fuentes ("porque lo sé")

  Un dueño de bar SÍ va a confiar en un agente que:
  ✅ Le habla como otro dueño de bar
  ✅ Entiende su estrés en hora pico
  ✅ Le responde rápido y claro
  ✅ Sabe lo que es un "variance de aguardiente"

  La personalidad correcta = adopción del producto.
  La personalidad incorrecta = el cliente no lo usa.
```

---

## 🏗️ Desarrollo de R2 Autonomous — Paso a paso

### Paso 1: El núcleo — Orquestador de herramientas (semana 1)

El cerebro del agente. Le da al LLM la capacidad de ejecutar acciones.

```text
🧠 ARQUITECTURA DEL NÚCLEO
─────────────────────────────────────────

                    ┌──────────────────────┐
                    │   Usuario escribe     │
                    │   "Genera una demanda │
                    │   por despido injusto"│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   🧠 LLM (Ollama)    │
                    │   Recibe el mensaje  │
                    │   + herramientas     │
                    │   disponibles        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   ⚙️ Tool Router     │
                    │   Decide qué hacer:  │
                    │                      │
                    │   ¿Usar herramienta? │
                    │   Sí → Ejecuta y     │
                    │        sigue         │
                    │   No → Responde      │
                    │        directamente  │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ 📄 File Sys  │ │ 🗄️ Database │ │ 🌐 Internet  │
     │ Leer/escribir│ │ Consultar    │ │ Buscar info  │
     │ documentos   │ │ BD del caso  │ │ Jurisprudencia│
     └──────────────┘ └──────────────┘ └──────────────┘
```

**Lo que se construye:**
```python
# tools/orquestador.py
class ToolOrchestrator:
    """Permite que el LLM ejecute herramientas de forma segura."""
    
    tools = {
        "read_file": leer_archivo,
        "write_file": escribir_archivo,
        "query_db": consultar_base_datos,
        "search_web": buscar_internet,
        "generate_doc": generar_documento,
        "send_whatsapp": enviar_whatsapp,
    }
    
    def ejecutar(self, comando: dict) -> str:
        """Ejecuta una herramienta y devuelve el resultado."""
        herramienta = comando["tool"]
        parametros = comando["params"]
        return self.tools[herramienta](**parametros)
```

### Paso 2: Memoria persistente (3 días)

El agente recuerda quién eres, qué has hablado, qué prefieres.

```text
💾 ESTRUCTURA DE MEMORIA
─────────────────────────────────────────

  SQLite (local, simple, sin servidor)

  Tablas:
  ┌─────────────────────────────────────┐
  │ sesiones:                           │
  │ id, usuario_id, creada_en, activa   │
  ├─────────────────────────────────────┤
  │ mensajes:                           │
  │ id, sesion_id, rol, contenido,       │
  │ herramientas_usadas, created_at     │
  ├─────────────────────────────────────┤
  │ memoria_larga:                      │
  │ id, usuario_id, clave, valor        │
  │ "nombre_cliente" → "Juan Pérez"     │
  │ "casos_activos" → "3"              │
  ├─────────────────────────────────────┤
  │ aprendizaje:                        │
  │ id, usuario_id, feedback, contexto  │
  │ "La última demanda que generé       │
  │  quedó bien, pero mejorar los       │
  │  hechos"                            │
  └─────────────────────────────────────┘
```

### Paso 3: Interfaz web conversacional (1 semana)

El chat donde el usuario habla con el agente.

```text
🖥️ COMPONENTES DE LA INTERFAZ
─────────────────────────────────────────

  Frontend (React):
  ┌─────────────────────────────────────┐
  │  💬 R2 Autonomous                   │
  │                                     │
  │  Mensajes como WhatsApp             │
  │  ├── Usuario: "Haz una demanda"     │
  │  ├── 🤖 "Claro, deme los datos..." │
  │  └── Input de texto + 🎤 micrófono  │
  │                                     │
  │  📎 Subir archivos (PDF, DOCX)      │
  │  📸 Subir imágenes                  │
  │  📋 Historial de conversaciones     │
  └─────────────────────────────────────┘

  Backend (FastAPI):
  POST /api/chat → Procesa mensaje
  GET  /api/history → Historial
  POST /api/upload → Subir archivo
  GET  /api/tools → Herramientas disponibles
```

### Paso 4: Sistema de especialidades (2 días)

El corazón de la versatilidad. Un mismo agente con diferentes "personalidades".

```text
🧬 ESPECIALIDADES
─────────────────────────────────────────

  ┌─────────────────────────────────────┐
  │  R2 Autonomous Engine               │
  │                                     │
  │  ┌─────────────────────────────┐    │
  │  │  🧠 System Prompt           │    │
  │  │  (personalidad base)        │    │
  │  └─────────────────────────────┘    │
  │                                     │
  │  📂 Especialidades instalables:     │
  │                                     │
  │  ⚖️ Legal:                          │
  │     ├── Prompt: "Eres un abogado..."│
  │     ├── Tools: generar_demanda,     │
  │     │         calcular_pension      │
  │     └── Knowledge: CST, CGP,        │
  │                   jurisprudencia    │
  │                                     │
  │  🧾 BarOS:                          │
  │     ├── Prompt: "Eres un           │
  │     │  bartender..."               │
  │     ├── Tools: consultar_ventas,    │
  │     │         controlar_stock       │
  │     └── Knowledge: productos,       │
  │                   precios           │
  │                                     │
  │  📢 Marketing:                      │
  │     ├── Prompt: "Eres un           │
  │     │  marketer..."                │
  │     ├── Tools: generar_post,        │
  │     │         programar_publicacion │
  │     └── Knowledge: perfiles,        │
  │                   campañas          │
  └─────────────────────────────────────┘
```

**Cada especialidad es un archivo JSON:**

```json
{
  "id": "legal-laboral",
  "nombre": "Asistente Legal Laboral",
  "version": "1.0",
  "personalidad": {
    "tono": "formal",
    "tuteo": "usted",
    "humor": "ninguno",
    "empatia": "profesional"
  },
  "prompt": "Eres un abogado senior con 20 años...",
  "tools": ["generar_demanda", "calcular_pension", "consultar_terminos"],
  "knowledge": {
    "laws": ["cst.pdf", "cgp.pdf"],
    "jurisprudencia": ["corte_suprema_2025.pdf"]
  },
  "modelo_recomendado": "qwen2.5:7b"
}
```

**Instalar una especialidad = copiar un JSON + sus datos.**

### Paso 5: Empaquetado (2 días)

El agente listo para distribuir.

```text
📦 ESTRUCTURA DEL PAQUETE
─────────────────────────────────────────

📁 R2-Autonomous-v1.0/
│
├── 📦 Instalador
│   ├── install.sh (macOS/Linux)
│   ├── install.bat (Windows)
│   └── Instalador.exe (Windows, opcional)
│
├── 🧠 Motor
│   ├── r2-engine (binario compilado)
│   ├── tools/ (herramientas base)
│   └── memory/ (base de datos SQLite)
│
├── 🌐 Web
│   ├── backend/ (FastAPI)
│   └── frontend/ (React compilado)
│
├── 🧬 Especialidades
│   ├── legal-laboral.json
│   ├── baros.json
│   ├── marketing.json
│   └── personalizadas/ (para clientes)
│
├── 📖 Documentación
│   ├── manual.pdf
│   └── ejemplos/
│
└── ⚙️ Configuración
    └── config.yaml
```

### Instalación en 5 pasos

```text
⬇️ PASO 1: Descargar
  • Cliente recibe: USB o link de descarga
  • Tamaño: ~50 MB (sin modelos)
  • Más modelos: ~2-5 GB adicionales

▶️ PASO 2: Ejecutar instalador
  • Windows: doble clic en install.bat
  • Mac: abrir terminal, ./install.sh
  • Linux: ./install.sh

⚙️ PASO 3: Configurar especialidad
  • Al iniciar, pregunta:
    "¿Qué especialidad quieres instalar?"
    1. ⚖️ Legal (laboral, civil, familia)
    2. 🧾 BarOS (gestión de bares)
    3. 📢 Marketing (redes sociales)
    4. 🎯 Personalizada (cargar archivo)
    
  • Si elige Legal:
    "¿Qué ramas del derecho?"
    ☑ Laboral
    ☐ Civil
    ☐ Familia
    ☐ Penal

📚 PASO 4: Cargar conocimiento
  • "Sube los documentos de tu firma
     para que el agente aprenda tu estilo"
  • Arrastra: demandas, poderes, contratos
  • La IA los procesa y aprende

🚀 PASO 5: ¡Listo!
  • "Abre http://localhost:3000
     para empezar a hablar con tu agente"
  • Chat funcionando en 5 minutos
```

### Configuración para cualquier especialidad

```text
🎯 CREAR UNA NUEVA ESPECIALIDAD
─────────────────────────────────────────

  Cualquier persona puede crear una especialidad nueva.
  Solo necesita:

  1. Un JSON con la personalidad (10 minutos)
  2. Los documentos de conocimiento (los que tenga)
  3. Definir qué herramientas necesita

  Ejemplo: "Quiero un agente para mi consultorio médico"

  medico.json:
  {
    "id": "medico-general",
    "nombre": "Asistente Médico",
    "personalidad": {
      "tono": "cálido",
      "tuteo": "usted",
      "humor": "poco",
      "empatia": "muy cálida"
    },
    "prompt": "Eres un médico con 15 años de experiencia...",
    "tools": ["gestionar_citas", "historial_paciente"],
    "knowledge": {
      "protocolos": ["protocolos_medicos.pdf"]
    }
  }

  → Copias el JSON a la carpeta especialidades/
  → Cargas los documentos de conocimiento
  → El agente ya sabe de medicina
  → Sin programar, sin compilar, sin instalar nada más
```

### ¿Qué tamaños de modelo usar?

```text
🧠 RECOMENDACIONES POR ESPECIALIDAD
─────────────────────────────────────────

  ⚖️ Legal:       Qwen2.5-7B (4 GB RAM)
                   → Suficiente para documentos legales
                   → Preciso, confiable

  🧾 BarOS:        Qwen2.5-1.5B (1.5 GB RAM)
                   → Consultas rápidas, comandos de voz
                   → Ligero, corre en cualquier PC

  📢 Marketing:    GPT-4o / Claude (API cloud)
                   → Contenido creativo de alta calidad
                   → O: Qwen2.5-7B para respuestas locales

  🏢 Enterprise:   Qwen2.5-14B (8 GB RAM, Mac Mini)
                   → Mayor precisión legal
                   → Documentos complejos

  Todos los modelos son configurables.
  El usuario elige según su hardware y necesidades.
```

### Resumen del desarrollo

```text
📋 SPRINTS DE DESARROLLO
─────────────────────────────────────────

  Sprint 1 (1 semana):   🧠 Núcleo + herramientas
  Sprint 2 (3 días):     💾 Memoria persistente
  Sprint 3 (1 semana):   💬 Interfaz web conversacional
  Sprint 4 (2 días):     🧬 Sistema de especialidades
  Sprint 5 (2 días):     📦 Empaquetado + instalador

  Total: ~3-4 semanas para MVP funcional.

  Después:
  • Especialidad Legal (semana 5)
  • Especialidad BarOS (semana 6)
  • Especialidad Marketing (semana 7)
  • Personalización Enterprise (semana 8)
```

---

## 🔒 Seguridad — Control de acceso y prevención de riesgos

Un agente con herramientas es poderoso. Un agente sin seguridad es peligroso.

### Principios de seguridad

```text
🛡️ CERO CONFIANZA (Zero Trust)
─────────────────────────────────────────

  El agente no confía en nadie por defecto.
  Cada acción se valida antes de ejecutarse.

  🚫 No ejecuta comandos sin verificar
  🚫 No accede a archivos sin permiso
  🚫 No envía mensajes sin confirmación
  🚫 No comparte información entre sesiones
```

### Niveles de acceso

```text
🔑 NIVELES DE PERMISOS
─────────────────────────────────────────

  NIVEL 0 — Solo conversación (seguro por defecto)
    • El agente solo habla. No ejecuta nada.
    • Ideal para: consultas rápidas, información general
    • Riesgo: ninguno

  NIVEL 1 — Lectura (bajo riesgo)
    • El agente puede LEER archivos y consultar la BD
    • NO puede escribir, modificar ni eliminar
    • Ideal para: abogados revisando información
    • Riesgo: bajo (fuga de información)

  NIVEL 2 — Lectura + Escritura controlada (riesgo medio)
    • El agente puede LEER y ESCRIBIR archivos
    • Siempre en carpetas designadas (sandbox)
    • Las escrituras requieren confirmación
    • Ideal para: generar documentos, tomar notas
    • Riesgo: medio (datos incorrectos)

  NIVEL 3 — Acción autónoma (riesgo alto)
    • El agente puede ejecutar comandos libremente
    • Enviar WhatsApp, modificar BD, ejecutar scripts
    • Cada acción se loguea y es reversible
    • Ideal para: automatización de procesos conocidos
    • Riesgo: alto (requiere supervisión)
```

### Sandboxing de archivos

```text
📁 SANDBOX
─────────────────────────────────────────

  El agente SOLO puede acceder a estas carpetas:

  ✅ DOCUMENTOS:     /home/abogado/casos/
  ✅ PLANTILLAS:     /home/abogado/plantillas/
  ✅ TEMP:           /tmp/r2-temp/

  ❌ NO PUEDE ACCEDER A:
     ❌ /etc/ (configuración del sistema)
     ❌ /usr/ (binarios del sistema)
     ❌ ~/.ssh/ (llaves privadas)
     ❌ C:\Windows\ (sistema operativo)
     ❌ Cualquier carpeta fuera de las permitidas
```

### Control de acciones peligrosas

```text
⚠️ ACCIONES QUE SIEMPRE REQUIEREN CONFIRMACIÓN
─────────────────────────────────────────

  🔴 Enviar WhatsApp o email
     → "¿Confirmas que quieres enviar este mensaje a 50 contactos?"

  🔴 Modificar o eliminar documentos
     → "¿Eliminar el archivo Demanda.pdf? No se puede deshacer."

  🔴 Ejecutar comandos del sistema
     → "¿Ejecutar script_de_migracion.sh?"

  🔴 Compartir información entre usuarios
     → "¿Compartir el caso de Juan Pérez con María García?"

  🟡 Acciones que NO requieren confirmación:
     → Leer documentos (Nivel 1)
     → Consultar base de datos
     → Generar borradores (no guardados)
     → Buscar en internet
```

### Auditoría (log de todo)

```text
📋 REGISTRO DE AUDITORÍA
─────────────────────────────────────────

  Cada acción del agente queda registrada:

  ┌─────────────────────────────────────────────┐
  │ 📅 15 Jul 2026 19:30:22                     │
  │ 👤 Usuario: Xavier                          │
  │ 🛠️ Herramienta: generate_document           │
  │ 📄 Acción: Creó Demanda por despido injusto │
  │ 📁 Archivo: Casos/JuanPerez/Demanda.docx    │
  │ ✅ Resultado: Éxito                         │
  │ ⏱️ Duración: 3.2 segundos                   │
  │ 🔍 UUID: a1b2c3d4-e5f6-7890                 │
  └─────────────────────────────────────────────┘

  El log es:
  • Inmodificable (solo append)
  • Exportable a PDF
  • Consultable por el admin
  • Evidencia en caso de disputa
```

### Para Enterprise (firmas de abogados)

```text
🏢 SEGURIDAD EMPRESARIAL
─────────────────────────────────────────

  🔐 CLIENTE VS AGENTE
     • El agente sabe quién es cada usuario
     • Un abogado NO puede ver los casos de otro
     • Solo el admin (socio de la firma) ve todo

  🏛️ CUMPLIMIENTO LEGAL
     • Habeas Data: los datos se quedan en la firma
     • Reserva profesional: el agente no comparte info
     • Cadena de custodia: todo queda registrado
     • RGPD / Ley 1581: datos personales protegidos

  🔒 CIFRADO
     • Documentos: cifrados en reposo (AES-256)
     • Comunicaciones: localhost (sin red externa)
     • BD: SQLite cifrada con clave de la firma
     • Backups: cifrados antes de salir
```

### Modo avión (seguridad máxima)

```text
✈️ MODO AVIÓN
─────────────────────────────────────────

  El agente funciona SIN NINGUNA conexión externa:
  • Sin internet
  • Sin APIs externas
  • Sin WhatsApp
  • Sin búsqueda web

  Solo el LLM local + los documentos de la firma.
  Ideal para:
  • Firmas que manejan información clasificada
  • Casos de alto perfil
  • Clientes que exigen confidencialidad total
```

### Panel de control de seguridad

```text
⚙️ ADMIN — Seguridad
─────────────────────────────────────────

  ┌─────────────────────────────────────────────┐
  │  🔒 SEGURIDAD Y PERMISOS                    │
  │                                             │
  │  Nivel de acceso actual: [Nivel 2 ▼]       │
  │                                             │
  │  Usuarios:                                   │
  │  👤 Xavier       🔑 Admin    🟢 Activo     │
  │  👤 María        🔑 Abogado  🟢 Activo     │
  │  👤 Carlos       🔑 Abogado  🔴 Inactivo   │
  │  👤 Asistente    🔑 Lectura  🟢 Activo     │
  │                                             │
  │  Carpetas permitidas:                       │
  │  📁 /home/abogado/casos/                    │
  │  📁 /home/abogado/plantillas/               │
  │  📁 /tmp/r2-temp/                           │
  │  [➕ Agregar carpeta]                        │
  │                                             │
  │  🔍 Auditoría: [📥 Exportar log completo]  │
  └─────────────────────────────────────────────┘
```
