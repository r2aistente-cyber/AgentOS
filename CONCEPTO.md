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
