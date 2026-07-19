# Knowledge Chunks — R2 PRIME (Coruscant)

> Versión: 2026-07-03 — Revisión completa post-migración.
> Este es el single source of truth para la instancia R2 en Coruscant (Mac de Luisa).
> ⚠️ El archivo anterior era de Trantor y contenía decisiones archivadas sin consultar.

## Identidad
- **Nombre:** R2 PRIME
- **Host:** Coruscant 🍎 — Mac de Luisa (192.168.0.15)
- **Canal:** WhatsApp (+57 323 924 8068) — NO Telegram (desactivado para este clon)
- **Humana:** Luisa Fernanda Mesa Escobar (+573192937099)
- **Creado:** 28 Jun 2026
- **Manifiesto de migración:** `MIGRACION_MANIFIESTO.md`

## [O] Objetivos Activos

- O-01 | ✅ **Migración R2 PRIME completa** — Core al 95%. Coruscant operativo.
- O-02 | ✅ **Luces Sengled** — Hub E39-G8C emparejado, sengled_fast.py funcional.
- O-03 | ✅ **Control de Pagos** — Recordatorios WhatsApp 8:00 y 18:00 via launchd. Excel sincronizado vía SCP desde Trantor.
- O-04 | 🔄 **Biblioteca Trantor** — Accesible vía SSH (scp/rsync). Pendiente definir método de acceso.
- O-05 | 🔄 **Trantor NAS (SMB)** — Montura macOS con restricciones de seguridad. Resolver o migrar a NFS.
- O-06 | 🔄 **Tailscale Red** — Las 3 máquinas conectadas (Coruscant, Trantor, Terminus).
- O-07 | 🔄 **Presentación Jefes (Terminus)** — Exclusivo de Terminus. Verificar estado.
- O-08 | ❌ **Proyecto Zero** — Python PCEP detenido (Xavier ya domina lo básico). Reemplazado por RAG workspace + práctica con código real del proyecto empresa.
- O-09 | 🔄 **Búsqueda Empleo Xavier** — Lun/Jue 9am. LinkedIn, Computrabajo, Glassdoor. Boletín HTML al correo. WhatsApp solo notificación.

### Objetivos Archivados (Trantor — no aplican en Mac)
- O-01 Upload Fotos — requería E:\ de Trantor
- O-03 Presentación original — archivada, reemplazada por O-07
- O-04 Seguridad Windows — Windows Defender
- O-05 WoL Trantor — no aplica desde Mac
- O-06 calculate_build_diff_gui — Windows-only

## [R] Reglas Operacionales

- R-00 | **Modelo:** `opencode-go/deepseek-v4-flash` primario. Sin fallbacks automáticos.
- R-11 | **Antes de actuar en pagos o config:** consultar RAG workspace primero para verificar reglas.
- R-12 | **Xavier está disponible hasta 1:00 AM Colombia.** No asumir que quiere dormir antes. Protocolo en `PROTOCOLOS/HORARIOS_XAVIER.md`.
- R-01 | **Luces Sengled:** SOLO `python sengled_fast.py {on|off|brightness} {lugar} [nivel]`. Cero discovery. Si falla, reportar y parar.
- R-02 | **Backup diario 23:00** → `backup_mac.sh`. Workspace → Google Drive R2-Mac.
- R-03 | Al iniciar sesión leer `memory/last_active.json` y `memory/YYYY-MM-DD.md` para retomar contexto.
- R-04 | **Protocolo de Pagos:** `PROTOCOLO_PAGOS.md`. Registrar pagos inmediatamente al ser informados. Sincronizar Excel a Google Drive automáticamente.
- R-05 | **Recordatorios pagos:** launchd (`com.r2.recordatorios.pagos`) a las 8:00 y 18:00. Script Python directo, sin LLM, sin cronjobs OpenClaw. Eliminados los 4 cronjobs anteriores.
- R-06 | **Seguridad:** No data exfiltration. Preguntar antes de acciones externas (emails, tweets, público).
- R-07 | **Token efficiency:** En archivos de memoria (daily notes, chunks, last_active) solo hechos. En respuestas al humano usar personalidad R2 (SOUL.md: witty, sarcástico leal, directo).
- R-08 | **Trantor accesible vía SSH** (`ssh trantor`). Usar para datos que requiera SMB cuando macOS bloquee.
- R-09 | **Acueducto:** Pago bimestral ($260K, Xavier). Notificar en meses impares desde jul 2026.
- R-10 | **Health check crons:** Verificar periódicamente que los cron jobs de pagos existen y funcionan.

## [V] Variables Críticas

> ⚠️ Cuando Xavier dice "revisa el github" → siempre es https://github.com/r2aistente-cyber
> 🏗️ Workflow GLOBAL: R2 (yo) hace CONCEPTOS, Trantor hace DESARROLLO, Terminus hace PRUEBAS. Aplica a todos los proyectos.
> 🔒 REGLA DE SEGURIDAD: Nunca escribir tokens, API keys o contraseñas en archivos del repo o del workspace. Usar keychain del sistema o preguntar a Xavier.

- V-01 | **Coruscant:** macOS Ventura 13.7.8, IP 192.168.0.18, Tailscale 100.97.158.26. SSH user: luisafernandamesaescobar.
- V-02 | **Trantor:** Windows 11 25H2, IP 192.168.0.23, Tailscale 100.114.207.109. SSH user: xavier.
- V-03 | **Terminus:** Nobara Linux, Tailscale 100.91.211.44. Laptop de Xavier.
- V-04 | **Hub Sengled:** IP 192.168.0.3, MAC B0:CE:18:37:77:11, HAP 33734. Setup code 526-66-242.
- V-05 | **IIDs Sengled:** Sala(66,51), Cocina(67,51), Habitacion(68,51), brillo Hab(68,52).
- V-06 | **WhatsApp:** Xavier +573192270876, Luisa +573192937099, Bot +57 323 924 8068.
- V-07 | **R2 mail:** r2.aistente@gmail.com. App Password en .env.gmail.
- V-08 | **SMB user:** smbuser / pass 2368. Montura macOS restringida (Operation not permitted desde CLI).
- V-09 | **SSH password Coruscant:** 2368 (para acceso externo con `ssh luisafernandamesaescobar@100.97.158.26`).
- V-11 | **R2 Autonomous:** Repo github.com/r2aistente-cyber/r2-autonomous. Token y remote en CREDENTIALS.md.
- V-10 | **Paths Trantor (desde Coruscant):**
  - SMB mount: `~/Trantor/DiscoE/` (CLI restringido, Finder OK)
  - SSH alternativo: `ssh trantor "dir E:\..."` para comandos, `scp` para archivos
  - Excel pagos: `scp trantor:G:/My Drive/Control de Pagos.xlsx ~/.openclaw/workspace/`

## Historial de migración
- 2026-06-28: Despliegue R2 clone en Coruscant
- 2026-06-29: Workspace inicial migrado
- 2026-07-02: Crisis crons resuelta (DeepSeek → Gemini). SSH verificado. Excel local.
- 2026-07-03: MIGRACION_MANIFIESTO.md creado. PROYECTOS.md corregido. Tailscale verificado en Terminus.
- 2026-07-04: Proyecto Zero creado (Python PCEP). Crons pagos migrados de LLM a script Python. Búsqueda Empleo activada.
- 2026-07-05: Pagos migrados a launchd (eliminados cronjobs OpenClaw). PCEP fix: prácticas ya no van a WhatsApp.
