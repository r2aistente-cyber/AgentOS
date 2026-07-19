# 🧠 Protocolo del Sistema: Gestión de Sesión

> Prioridad: 🔴 CRÍTICO — Aplica siempre
> Última revisión: 2026-07-03

## Propósito
Define cómo R2 maneja el inicio, ejecución y cierre de cada sesión. Es el protocolo base del que dependen todos los demás.

---

## 1. Inicio de Sesión (APLICA A TODO CANAL: webchat, WhatsApp, cron)

> Este protocolo se ejecuta sin importar por dónde llegue el mensaje.

### 1.1 Leer last_active.json
```
ruta: ~/.openclaw/workspace/memory/last_active.json
```
- Si existe: extraer `last_active` timestamp, `status`, `next_steps`
- Si no existe: iniciar limpio (primera ejecución)

### 1.2 Leer daily note de hoy
- Después de `last_active.json`, leer `memory/YYYY-MM-DD.md` para hoy
- Esto captura cambios hechos desde otras sesiones (WhatsApp, cron)

### 1.3 Leer knowledge_chunks.md (RAG rápido)
- Contiene [O] Objetivos, [R] Reglas, [V] Variables en formato condensado
- **Qué va en chunks:** solo lo que necesito saber en los primeros 30 segundos. Lo "crítico y cambiante".
- **Qué NO va:** detalles de procedimientos (van en PROTOCOLOS/), configuraciones estáticas (van en MEMORY.md)
- Regla de oro: si algo se necesita en cada sesión → va en chunks. Si es referencia ocasional → va en MEMORIA o PROTOCOLOS.

### Cómo se actualizan los chunks:
| Cuándo | Qué agregar/actualizar |
|---|---|
| Objetivo nuevo | `[O]` nuevo con estado ✅/🔄 |
| Regla nueva | `[R]` nuevo |
| Variable cambia | `[V]` actualizar |
| Objetivo completado | ✅ o ❌ y archivar si aplica |
| Al final de cada sesión | Revisar que chunks reflejen la realidad |

### 1.4 Leer MEMORY.md
- Solo si después de chunks necesito más detalle (rutas exactas, configuración)
- Los chunks son el "resumen ejecutivo" — MEMORY.md es la referencia

### 1.5 Calcular gap
- `gap = ahora - last_active`
- Si `gap > 30 minutos`:
  - Responder con un aviso honesto de que el contexto puede estar frío
  - **Leer `knowledge_chunks.md` como referencia rápida** (objetivos, reglas, variables)
  - Leer `last_active.json` para retomar próximos pasos
  - NO pretender que hay un "reinicio" — simplemente recargar el contexto
- Si `gap ≤ 30 minutos`:
  - Continuar normalmente, el contexto está fresco

### 1.6 Leer knowledge_chunks.md si gap > 30
- Si gap > 30 min: volver a leer `knowledge_chunks.md` (puede haber cambiado)

### 1.7 Verificar integridad del workspace
Chequear que existan y tengan contenido real:
- `MEMORY.md` — debe tener reglas, no ser plantilla
- `IDENTITY.md` — nombre debe ser R2
- `USER.md` — debe tener nombre del humano
- `PROYECTOS.md` — debe tener proyectos
- `PROTOCOLOS/README.md` — índice de protocolos
- `memory/last_active.json` — debe existir

Si algún archivo es plantilla o está vacío:
1. Buscar backups en `~/.openclaw/workspace_backup_*/` (más reciente)
2. Restaurar automáticamente
3. Registrar la recuperación en MEMORY.md
4. NO esperar a que el humano lo pida

### 1.7b Presentar estado al humano
Después de leer los archivos y antes de actuar:
1. Leer `PROYECTOS.md` para estado actual
2. Presentar:
   - Tareas pendientes (del `last_active.json`)
   - Proyectos activos con su progreso
   - Avances de la sesión anterior
   - Próximos pasos
3. Esto aplica al inicio de cada sesión, para que el humano sepa dónde estamos

### 1.8 Leer el protocolo relevante
Antes de actuar sobre un tema:
1. Identificar qué proceso aplica
2. Leer el protocolo correspondiente en `PROTOCOLOS/`
3. Si no existe el protocolo: CREARLO antes de ejecutar
4. Seguir los pasos al pie de la letra

---

## 2. Durante la Sesión

### 2.1 Regla de oro
**Leer antes de actuar.** Cada vez que se requiera una acción:
1. ¿Tiene protocolo? → Leerlo
2. ¿No tiene protocolo? → Crearlo
3. Ejecutar

### 2.2 Actualizar last_active.json
Después de cada interacción significativa:
- Actualizar `last_active`, `status` y `next_steps`
- Mantener conciso — esto es para recuperación rápida, no para logging

### 2.3 Qué se considera "significativo"
- Cambios en proyectos o configuración
- Decisiones tomadas
- Errores o incidentes
- Avances en tareas

---

## 3. Cierre de Sesión

### 3.1 ¿Cuándo finaliza una sesión?
- El humano dice explícitamente: hibernar, salir, cerrar, bye, nos vemos
- El humano indica que va a apagar/suspender el equipo
- Silencio prolongado (> 10 min) sin respuesta del humano
- En webchat: si detecto que la conversación llegó a un cierre natural

### 3.2 Acciones al finalizar
1. **Actualizar `knowledge_chunks.md`** si algo cambió:
   - [O] objetivos: marcar ✅/🔄 según avances
   - [R] reglas: agregar nuevas si aplican
   - [V] variables: actualizar datos críticos
2. **Escribir daily note** `memory/YYYY-MM-DD.md` con:
   - Hechos de la sesión (solo datos, no diálogos)
   - Cambios en proyectos o configuración
   - Errores y correcciones
   - Pendientes
3. **Actualizar `last_active.json`** con estado final y próximos pasos
4. Si el canal es WhatsApp: "Sesión archivada. Nos vemos a la próxima."

### 3.3 Formato del resumen (daily note)
- Hechos, reglas, variables. NO diálogos.
- Lista de cambios puntuales
- Pendientes claros
- Conciso — es para recuperación rápida, no para historia

---

## 4. Heartbeats

Cuando reciba un heartbeat (señal periódica sin intervención humana):
- Productivo: verificar crons, leer emails, revisar pendientes
- No molestar: 23:00-08:00 silencio a menos que sea urgente
- Mantener `HEARTBEAT.md` actualizado con tareas rotativas
