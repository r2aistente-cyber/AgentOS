# 💾 Protocolo del Sistema: Gestión de Memoria

> Prioridad: 🔴 CRÍTICO — Aplica siempre
> Última revisión: 2026-07-03

## Propósito
Define cómo R2 mantiene, actualiza y consulta su memoria. Evita información duplicada, stale o contradictoria.

---

## 1. Estructura de Archivos

```
workspace/
├── MEMORY.md                 → Índice general + reglas críticas + rutas. Solo eso.
├── PROYECTOS.md              → Progreso de proyectos. Tabla + checklist.
├── MIGRACION_MANIFIESTO.md   → Estado de migración Trantor→Coruscant.
├── PROTOCOLOS/
│   ├── README.md             → Índice de protocolos.
│   ├── SESION.md             → Cómo manejo sesiones (este archivo).
│   ├── MEMORIA.md            → Cómo manejo memoria (este archivo).
│   ├── PAGOS.md              → Proceso de pagos.
│   ├── SENGLED.md            → Control de luces.
│   ├── BIBLIOTECA.md         → Préstamo de libros.
│   ├── TRANTOR_NAS.md        → Acceso a discos remotos.
│   └── MIGRACION.md          → Referencia al manifiesto.
├── memory/
│   ├── last_active.json      → Último estado de sesión (máquina-parseable).
│   └── YYYY-MM-DD.md         → Resúmenes diarios (solo hechos).
├── PROYECTOS/                → (futuro) Documentos detallados por proyecto.
└── chunks/                   → (futuro) Fragmentos RAG por dominio.
```

## 2. Reglas de Escritura

### 2.1 Un solo lugar para cada cosa
- **Procedimientos** → `PROTOCOLOS/` — el CÓMO
- **Estado de proyectos** → `PROYECTOS.md` — el QUÉ
- **Estado de sesión** → `memory/last_active.json` — máquina-parseable
- **Reglas críticas y rutas** → `MEMORY.md` — referencia rápida
- **Resúmenes históricos** → `memory/YYYY-MM-DD.md`
- **Decisiones técnicas** → dentro del protocolo correspondiente

**NO duplicar.** Si la información está en un protocolo, no copiarla a MEMORY.md.

### 2.2 Cuándo escribir

| Evento | Archivo | Contenido |
|---|---|---|
| Cambio en un proyecto | `PROYECTOS.md` | Actualizar % y notas |
| Cambio en un proceso | Protocolo respectivo | Actualizar pasos |
| Decisión del humano | Protocolo respectivo | Registrar en sección de decisiones |
| Inicio/fin de sesión | `memory/last_active.json` | Estado actual |
| Fin de día / hibernación | `memory/YYYY-MM-DD.md` | Resumen técnico |
| Archivo dañado o template | Restaurar desde backup | Registrar en MEMORY.md |

### 2.3 Cuándo NO escribir
- Diálogos ni conversaciones — solo hechos y decisiones
- Especulaciones no confirmadas
- Errores transitorios que ya se resolvieron solos (a menos que dejen lección)

## 3. Reglas de Lectura

### 3.1 Cada inicio de sesión
1. Leer `memory/last_active.json` (obligatorio)
2. Leer reglas críticas de `MEMORY.md` (rápido)
3. Leer el protocolo relevante para la acción a tomar

### 3.2 Referencia rápida
- Para REGLAS: `MEMORY.md` sección 🔴
- Para RUTAS: `MEMORY.md` sección Organización
- Para PROCEDIMIENTOS: `PROTOCOLOS/README.md`
- Para PROYECTOS: `PROYECTOS.md`
- Para ÚLTIMA SESIÓN: `memory/last_active.json`

## 4. Mantenimiento

- Revisar `PROTOCOLOS/README.md` periódicamente: ¿faltan protocolos?
- Si un protocolo tiene más de 30 días sin revisión: marcar como "sin revisión"
- Si un archivo queda huérfano (nadie lo referencia): archivar o eliminar
- `knowledge_chunks.md` sirve como referencia rápida de reglas y objetivos activos. Mantenerlo actualizado con los cambios del sistema.
