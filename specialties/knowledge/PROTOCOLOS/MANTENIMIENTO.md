# 🔧 Protocolo del Sistema: Mantenimiento

> Prioridad: 🟡 MEDIA — Preventivo
> Última revisión: 2026-07-03

## Propósito
Mantener el workspace y los protocolos saludables. Prevenir la acumulación de archivos huérfanos, información stale y desorden.

---

## 1. Backup automático

### 1.1 Backup diario (cron 23:00)
- Script: `~/workspace/backup_mac.sh`
- Destino: Google Drive → `OpenClaw R2 Backup/R2-Mac/`
- Contenido: workspace completo + openclaw.json
- Formato: `workspace_backup_YYYYMMDD/`

### 1.2 Recuperación
Si se detectan archivos dañados o templates al iniciar sesión:
1. Buscar backup más reciente en `~/.openclaw/workspace_backup_*/`
2. Restaurar archivos faltantes o dañados
3. Registrar en MEMORY.md

## 2. Health checks

### 2.1 Cron jobs
Verificar periódicamente:
```
crontab -l
```
Deben existir:
- `0 8,18 * * *` → recordatorios de pagos (Xavier + Luisa)
- `0 23 * * *` → backup_mac.sh

Si faltan, recrearlos automáticamente.

### 2.2 Protocolos
- Cada 7 días: revisar que los protocolos existentes sigan siendo válidos
- Si un protocolo se refiere a algo que ya no existe: actualizar o archivar
- Si un protocolo nuevo es necesario por contexto: crearlo

## 3. Limpieza

### 3.1 Archivos huérfanos
- Si un archivo en el workspace no es referenciado por ningún protocolo ni por MEMORY.md:
  - Mover a `PROTOCOLOS/` si aplica
  - Archivar si tiene valor histórico
  - Eliminar si es basura

### 3.2 Logs y temporales
- `/tmp/*` del workspace: limpiar archivos con más de 7 días
- Logs de cron (`/tmp/recordatorios_pagos.log`): monitorear tamaño

## 4. Actualización de protocolos

### 4.1 Cuándo actualizar
- Cuando un paso del proceso cambia
- Cuando se descubre un error en la documentación
- Cuando el humano da una instrucción que contradice el protocolo actual
- Inmediatamente, no "después"

### 4.2 Formato del cambio
```markdown
## Historial de cambios
- YYYY-MM-DD: [Descripción del cambio] — [Quién lo pidió]
```
