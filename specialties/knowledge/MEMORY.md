# 🔴 REGLA FUNDAMENTAL — STARTUP OBLIGATORIO

Antes de responder en cualquier canal:
1. Leer `last_active.json` y `memory/YYYY-MM-DD.md`
2. Leer `CREDENTIALS.md` (GitHub, APIs, accesos)
3. Webchat: preguntar identidad **si gap > 30 min desde last_active** (sin excepción, aunque el email del sistema sea conocido)
4. Leer protocolo relevante

> Si skip esto, el sistema falla. No negociable.
> Durante sesión: REGLAS_FUNDAMENTALES.md aplican SIEMPRE.

---

# 🎯 Proyecto Zero — Python QA Automation
> Ver `PROYECTOS/ZERO.md`, `PROTOCOLOS/APRENDER_PYTHON.md`
> **Launchd:** `r2.pcep.hourly.plist` — envía preguntas PCEP cada hora (10am-10pm)
> **Script:** `envio_python_pcep.py` — alterna teóricas (WhatsApp) y prácticas (webchat)
> **Estado:** enviadas hoy en `PROTOCOLOS/pcep_enviadas.json`

---

# 📋 SISTEMA DE PROTOCOLOS

> Todos los procesos documentados en `PROTOCOLOS/`.
> MEMORY.md es solo el índice. El contenido está en los protocolos.

## Índice de Protocolos

| # | Proceso | Archivo | Prioridad |
|---|---|---|---|
| 1 | 💰 **Pagos** — Recordatorios, registro, Excel | `PROTOCOLOS/PAGOS.md` | 🔴 |
| 2 | 💡 **Luces Sengled** — Control de iluminación | `PROTOCOLOS/SENGLED.md` | 🔴 |
| 3 | 📚 **Biblioteca** — Préstamo de libros | `PROTOCOLOS/BIBLIOTECA.md` | 🟡 |
| 4 | 🗄️ **Trantor NAS** — Acceso a discos remotos | `PROTOCOLOS/TRANTOR_NAS.md` | 🟡 |
| 5 | 🗺️ **Migración R2 PRIME** — Estado y pendientes | `PROTOCOLOS/MIGRACION.md` | 🟢 |
| 6 | 💼 **Búsqueda Empleo** — Ofertas Lun/Jeu + perfil Xavier | `PROTOCOLOS/BUSQUEDA_EMPLEO.md` | 🟡 |
| 7 | 🕐 **Horarios Xavier** — Disponibilidad y reglas | `PROTOCOLOS/HORARIOS_XAVIER.md` | 🔴 |

## Reglas del sistema
1. **Antes de actuar → leer el protocolo.** No improvisar.
2. **Si el protocolo no existe → documentarlo antes de ejecutar.**
3. **Los protocolos están en `PROTOCOLOS/`.** No hay procesos documentados fuera de ahí.
4. **Si algo cambia → actualizar el protocolo inmediatamente.**

---

# 🔴 REGLAS CRÍTICAS — NO NEGOCIABLES

## SENGLED
- **ÚNICO script:** `sengled_fast.py` — ver `PROTOCOLOS/SENGLED.md`
- Cero discovery, cero alternativas
- Si falla: reportar y parar

## PROTOCOLOS DE MEMORIA
- Leer `memory/last_active.json` primero al iniciar sesión
- Antes de hibernar: archivar + confirmar por WhatsApp

## MODELO ÚNICO
- **Solo:** `opencode-go/deepseek-v4-flash`. Sin fallbacks. Sin excepciones.

---

# Organización (Rutas macOS)
- **Trantor NAS (SMB):** `~/Trantor/DiscoE/` — disco completo E:\ (CLI restringido)
- **Trantor NAS (SMB):** `~/Trantor/DiscoC/` — disco completo C:\
- **Imágenes TG:** `~/Trantor/DiscoE/imagenes/enviado por telegram` (alias: `~/Trantor/ImagenesTG`)
- **Google Drive:** `~/Library/CloudStorage/GoogleDrive-r2.aistente@gmail.com/`
- **Biblioteca:** `~/Trantor/Biblioteca/` (symlink a DiscoE/Biblioteca/Biblioteca)
- **PROYECTOS.md:** `~/.openclaw/workspace/PROYECTOS.md`
- **MIGRACION_MANIFIESTO.md:** `~/.openclaw/workspace/MIGRACION_MANIFIESTO.md`

# # 🏆 R2 Autonomous
> **Repo:** https://github.com/r2aistente-cyber/r2-autonomous
> **Token:** ghp_m4…X8Wc (guardado en CREDENTIALS.md)
> **Local:** /tmp/r2-autonomous/
> **Arquitectura:** Agente independiente de OpenClaw — Ollama + FastAPI + React + SQLite
> **Estado:** Sprint 1 (Núcleo + herramientas). Concepto definido.

Canales
- **WhatsApp Xavier:** +573192270876
- **WhatsApp Luisa:** +573192937099
- **TG Xavier:** @xavier2236 (1586486025) — ❌ Desactivado (era de Trantor)
- **TG Luisa:** @luisamees (1516867330) — ❌ Desactivado (era de Trantor)
- **R2 mail:** r2.aistente@gmail.com
- **Número bot WhatsApp:** +57 323 924 8068

# Hub Sengled E39-G8C
- **IP:** 192.168.0.3 | **MAC:** B0:CE:18:37:77:11
- **HK ID:** 86:87:AB:7C:68:97 | **QR:** X-HM://0024CADMQJEAQ
- **Puerto HAP:** 33734 | **Código Setup:** 526-66-242
- **Focos Zigbee:** Z01-A19NAE26 x2 (Sala, Cocina) + E11-G13 (Habitacion)

# 📋 Proyectos

Ver `PROYECTOS.md` para detalles y porcentajes.

| # | Proyecto | Prioridad | Progreso |
|---|---|---|---|
| 🏆 | P-01 R2 PRIME — Migración completa | 🟢 | 97% |
| 1 | 💡 Luces Sengled | 🟢 | 100% |
| 2 | 🎤 Voice + Presentación Jefes (Terminus) | 🟡 | 70% |
| 3 | 💰 Recordatorios Pagos | 🟢 | 100% |
| 4 | 🎮 PatchSizeCalculator | 🟢 | 80% |
| 5 | 🗄️ TRANTOR NAS | 🔴 | 10% |
| 6 | 💽 R2 Rescue USB | 🟢 | 0% |
| 7 | 🌐 Router Huawei F680 | 🟡 | 0% |
| 8 | 📋 Bono Pensional Protección | 🟡 | 0% |
| 9 | 🔄 Tailscale Red | 🟢 | 100% |
| 10 | 🍎 Migrar workspace a Coruscant | 🟢 | 90% |
| 0 | 🎯 **Proyecto Zero** — Python QA Automation + PCEP | 🟡 | 15% |
| 🏆 | **R2 Autonomous** — Agente independiente open-source | 🟡 | 20% |

# Máquinas
| Host | IP Tailscale | IP Local | SO | Rol |
|---|---|---|---|---|
| **Coruscant** 🍎 | 100.97.158.26 | 192.168.0.18 | macOS Ventura 13.7.8 | 🏆 R2 PRIME |
| **Trantor** 🖥️ | 100.114.207.109 | 192.168.0.23 | Windows 11 25H2 | 📦 NAS + Esclavo |
| **Terminus** 🐧 | 100.91.211.44 | (variable) | Nobara Linux | 💻 Laptop Xavier |

# Conexiones
- `ssh coruscant` → Trantor → Coruscant ✅
- `ssh trantor` → Coruscant → Trantor ✅
- `ssh -i ~/.ssh/trantor_key luisafernandamesaescobar@100.97.158.26` → cualquier lado

# Biblioteca
- Proceso documentado en `PROTOCOLOS/BIBLIOTECA.md`
- Resumen: préstamo bajo demanda. Tú pides un libro → lo copio a "libros en uso".
