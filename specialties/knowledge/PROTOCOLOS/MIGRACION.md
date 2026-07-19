# 🗺️ Protocolo: Estado de Migración R2 PRIME

> Prioridad: 🟢 COMPLETADA (core)
> Última revisión: 2026-07-03

## Propósito
Referencia rápida al estado de migración de R2 desde Trantor a Coruscant.

## Documento principal
Ver `MIGRACION_MANIFIESTO.md` en el workspace root para el detalle completo.

## Resumen ejecutivo
- ✅ Core migrado al 95% (workspace, scripts, crons, luces, SSH)
- ⚠️ Google Drive "Otras computadoras" es cloud-only en Mac (workaround: copia local)
- ⚠️ SMB bloqueado en macOS Ventura (workaround: SSH/SCP)
- 📋 Proyectos actualizados en PROYECTOS.md

## Pendientes reales (post-manifiesto)
1. Resolver Google Drive cloud-only (mover Excel a ubicación accesible)
2. Resolver SMB o migrar a NFS
3. Verificar Presentación Jefes (#2) en Terminus
