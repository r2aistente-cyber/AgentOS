# 🏗️ R2 Hub / AgentOS — Plan de Desarrollo v3.0

> **Reescrito:** 2026-08-04 — reemplaza v2.0.
> **Por qué:** v2.0 planeaba distribución como app nativa Tauri sin dependencias
> (Sprint 9 original, `EXPORT.md`, `APP.md`). Lo que realmente se construyó fue
> Hub Python + agentes en venv, con **NSSM** como supervisor de servicios en
> Windows para producción — un camino distinto, no una variación del original.
> Además, encima del MVP planeado se construyó un sistema completo de
> *specialties*/*skills*, multi-modelo, RAG, MCP genérico e ingesta legal que
> v2.0 no contemplaba en absoluto.
>
> Cada estado (`[x]`/`[ ]`) de este documento fue **verificado contra el código
> real** el 2026-08-04 (no contra el checklist anterior — ese había divergido
> en ambas direcciones: cosas marcadas pendientes que ya existían, y viceversa).

---

## 📊 Dónde está el proyecto, en una frase

MVP + frontend + logs/monitoreo + WhatsApp + Telegram + seguridad
(Sprints 1-2-3-4-5-6-6b-8) **cerrados y probados** (338 tests, verde). Encima
de eso, un sistema de specialties/skills/multi-modelo/RAG **no planeado y
también cerrado** (Sprint 10).
Lo que falta de verdad para poder llamarlo "terminado" está todo junto en el
**Sprint 11**, al final de este documento — es corto.

---

## ✅ Sprint 1 — Hub: Gestión de Agentes — cerrado

`hub/main.py` (FastAPI :8234), `agent_manager.py`, `agent_process.py`,
`health_checker.py`, `api/agents.py`. CRUD de agentes, start/stop/restart,
health checks, auto-restart. Sin cambios de fondo desde v2.0.

## ✅ Sprint 2 — Engine Base + LLM + Tools — cerrado

`hub/templates/`: LLM multi-proveedor (Ollama, OpenAI, Anthropic, OpenCode,
Custom + Mock), `ToolRegistry`/`ToolOrchestrator`, memoria SQLite por agente,
sandbox + permisos + audit. `POST /api/v1/chat`, `/health`, `/sessions`,
`/upload`, `/files` funcionales.

- [x] Extracción de contenido de adjuntos — **corregido respecto a v2.0, que
  lo daba como pendiente en bloque.** `hub/templates/file_extractor.py`
  soporta TXT/MD/JSON/CSV/PDF (pypdf)/DOCX (python-docx)/XLSX (openpyxl),
  enganchado en `POST /api/v1/upload` (`agent_main.py:215`). Lo único que
  falta de verdad es **imágenes (vision/OCR) y audio (transcripción)** — ver
  Sprint 11.

## 🟡 Sprint 3 — Frontend: Dashboard + Wizard — funcionalmente cerrado, 2 puntos sueltos

`frontend/` (React + Vite + TS): Dashboard, CreateWizard, AgentDetail,
ChatView, LogsView — todo implementado y en uso real (26+ commits activos).

- [ ] Diseño responsive — sin verificar (0 media queries en `frontend/src`)
- [ ] Estados loading/empty/error — sin verificar

*(Baja prioridad si el único consumo real sigue siendo `desktop_shell.py`
con pywebview a tamaño fijo — ver decisión de producto en Sprint 11.)*

## ✅ Sprint 4 — Logs, Monitoreo, Auto-Restart — cerrado

**Corregido respecto a v2.0**, que marcaba todo el sprint como pendiente pese
a estar hecho: `GET /agents/{name}/logs`, `GET /agents/{name}/logs/stream`
(SSE), `GET /agents/{name}/stats`, `GET /hub/stats` — todos en
`hub/api/agents.py`. Health checker con auto-restart operativo.

## ✅ Sprint 5 — Primer Agente Real — cerrado (y superado)

El plan original apuntaba a "R2 PRIME". En la práctica hay **3 agentes reales
registrados**: `R2` (9002), `Android_Dev` (9001), `r2-legal` (9000) — este
último con specialty propia, skills, RAG y conocimiento legal (ver Sprint 10).

## ✅ Sprint 6 — WhatsApp por Agente — cerrado

`hub/whatsapp_manager.py`: sidecar por agente, sesión independiente, QR,
start/stop/status. Implementado en su totalidad.

## ✅ Sprint 6b — Telegram por Agente — cerrado (2026-08-04, no estaba en v2.0)

A diferencia de WhatsApp, Telegram no necesita sidecar Node ni QR: solo habla
HTTP con la Bot API, así que corre **dentro del proceso del propio agente**
como long-polling en background (`hub/templates/telegram_bot.py`,
arrancado desde el `lifespan` de `agent_main.py` si
`channels.telegram.enabled`). Cada chat de Telegram se mapea 1:1 a una sesión
propia (`telegram:{chat_id}`), mismo patrón que usa el sidecar de WhatsApp
con el número de teléfono.

- [x] `channels.telegram.{enabled, bot_token, allowed_users}` en
  `default_config.yaml`
- [x] Whitelist por `chat_id` (`allowed_users`) — sin whitelist, el bot queda
  abierto a cualquiera (deliberado pero no es el default recomendado)
- [x] `bot_token` saneado en `hub/exporter.py` (mismo trato que `api_key`);
  `allowed_users` tratado como dato específico del dueño (no viaja en el export)
- [x] Tests: `tests/template/test_telegram_bot.py` (11 casos) +
  `tests/test_exporter.py::test_telegram_bot_token_no_viaja_en_el_export`
- [x] Fix de paso: ningún logger del engine (`engine.py`, `orchestrator.py`,
  ahora `telegram_bot.py`) tenía handler — faltaba `logging.basicConfig()`
  en `agent_main.py`, así que todo INFO/WARNING se perdía en silencio pese a
  que stdout/stderr del proceso ya se capturaba en `logs/agent.log`
- [x] **En producción real:** conectado al agente `R2` (bot `@R2_50802_Bot`)
  — un solo bot_token por agente, no compartido (Telegram no permite dos
  consumidores de `getUpdates` en el mismo token sin pisarse)
- [ ] UI: campo de `bot_token`/`allowed_users` en el wizard/`AgentDetail`
  (hoy se edita `config.yaml` a mano — funciona, pero no es autoservicio)

## 🔁 Sprint 7 / 9 — Empaquetado + Distribución — **reescrito, esto es lo que cambió de fondo**

### Lo que decía v2.0 (Sprint 9 original)
Paquete `.tar.gz` autocontenido con app nativa Tauri embebida, cero
dependencias salvo Ollama, ícono en bandeja del sistema, `r2 update`/
`r2 rollback`. Descrito en `EXPORT.md` y `APP.md` — **ninguno de los dos
refleja hoy la dirección real** (ver decisión pendiente en Sprint 11).

### Lo que existe de verdad (verificado 2026-08-04)
- [x] `install.bat` (Windows) — funcional
- [x] `hub/exporter.py` → `export_agent()`: `.tar.gz` con secretos saneados
  (`llm.api_key`, `search.brave_api_key`, `security.token`, `bot_token`
  strippeados)
- [x] `hub/importer.py` → `import_agent()`: extrae + configura + arranca
- [x] Export/import endurecido para **distribución cross-máquina**
  (commit `334c0b0`)
- [x] `Preparar-EntornoHub.ps1` — venv reproducible del Hub en máquina nueva
- [x] `scripts/Instalar-Servicios-NSSM.ps1` / `Desinstalar-...` — Hub y
  `mcp_gateway` como **servicios de Windows** corriendo como usuario `xavier`
  (no `LocalSystem`), parametrizable por servicio
- [x] Acceso directo de escritorio con ícono propio (`r2hub.ico`) y arranque
  **totalmente silencioso**: `Iniciar-R2Hub.bat` lanzaba Hub y frontend con
  `start /min` (sí llegaba a mostrar un flash de consola) y su propia
  consola quedaba visible mientras el usuario esperaba. Ahora Hub/frontend
  arrancan vía `Start-Process -WindowStyle Hidden` (oculto de verdad, sin
  flash, con stdout/stderr a `AgentOS/logs/`), y el acceso directo apunta a
  `Iniciar-R2Hub-Oculto.ps1` (`powershell -WindowStyle Hidden`) en vez del
  `.bat` directo — lo único visible al abrir el ícono es la ventana de la
  app. Verificado en esta máquina: único proceso con ventana visible es
  `python — "R2 Hub · AgentOS"`, cero `cmd`/`powershell` con ventana.

### Cross-platform (macOS/Linux) — arreglado hoy, 2026-08-04
`install.sh` **estaba roto de verdad**, no solo "sin probar": llamaba a
`bash Iniciar-R2Hub.sh` para arrancar el Hub, y ese archivo nunca existió en
el repo (solo `Iniciar-R2Hub.bat`, la versión Windows) — el instalador se
habría caído en el último paso, y el launcher de escritorio que crea también
habría quedado roto. Además `desktop_shell.py` (pywebview) nunca estuvo en
ningún `requirements.txt` — bug real también en Windows, no solo en Mac,
enmascarado porque ya estaba instalado a mano en el venv de esta máquina.

- [x] `Iniciar-R2Hub.sh` — creado (equivalente a `Iniciar-R2Hub.bat`: arranca
  Hub + Vite en background con `nohup`, espera con polling, abre la ventana
  pywebview)
- [x] `requirements-desktop.txt` — `pywebview` separado de
  `hub/requirements.txt` a propósito (ese archivo se reusa tal cual como
  requirements de cada agente *exportado*; un agente headless no necesita
  una librería de ventanas). `install.sh`/`install.bat` ahora instalan ambos.
- [x] Limpieza: `backend/memory/session.py` — archivo muerto de la v1
  (pre-migración a `hub/`) que había quedado trackeado en git por error,
  sin ninguna referencia en el código — eliminado.
- [ ] **Sigue sin correrse en una Mac/Linux real** — la revisión fue de
  código (rutas, imports, requirements), no una corrida end-to-end en el
  SO real. `pywebview` sí declara sus dependencias nativas de macOS
  (`pyobjc-framework-Cocoa`/`WebKit`) vía markers de plataforma en PyPI, así
  que debería resolverlas solo, pero falta confirmarlo con una instalación real.
- [ ] No hay equivalente a NSSM para correr el Hub como servicio en
  background en macOS (sería `launchd` + un `.plist`) — hoy no existe nada
  de eso; sin él, "instalar" en Mac significa `bash Iniciar-R2Hub.sh` cada
  vez, no un servicio que arranca solo.

### Lo que falta de verdad
- [ ] `update` — actualizar un agente exportado **in-place preservando
  memoria/config** (hoy `import_agent()` no distingue instalación nueva de
  actualización)
- [ ] `rollback` — volver a la versión anterior de un paquete importado

## ✅ Sprint 8 — Endurecimiento de Seguridad — cerrado 2026-07-23

Whitelist de `exec_command` + bypass patterns, sandbox aplicado también a
`exec_command`, gate de `requires_confirmation` en el orquestador, permisos
por agente, auth + bind `127.0.0.1` + CORS restringido (agente y Hub),
secretos saneados en export. Tests: `tests/s8/test_exec_security.py`,
`tests/test_security.py`.

- [ ] Único punto sin cerrar: **test dedicado de aislamiento cross-agente**
  del sandbox (un agente no puede tocar la carpeta de otro) — hoy es una
  propiedad que se cree cierta por diseño, no verificada por test.

---

## 🆕 Sprint 10 — Specialties, Skills, Multi-modelo y RAG legal — no estaba en v2.0, cerrado

Todo esto se construyó después del plan original y ya está en producción real
(agente `r2-legal`):

- [x] `hub/specialty_loader.py` — herencia de specialties (`_merge_specialty`,
  `_resolve_chain`), resolución de skills (`resolve_specialty`,
  `skills_summary`)
- [x] `specialties/core.json`, `specialties/r2-legal.json` +
  `specialties/knowledge/`
- [x] `skills/` — 7 skills en YAML (`derecho-general`, `busqueda-web`,
  `vision`, `analisis-archivos`, `asistente-escritura`, `datos-tabulares`,
  `lectura-documentos`), activación **bajo demanda** vía tool `activar_skill`
  (progressive discovery, no todo cargado de una)
- [x] Wizard: elegir specialty al crear un agente
- [x] Multi-modelo por agente + cambio en caliente + proveedor `opencode-go`
- [x] Sesiones de trabajo + persistencia de chat + medidor de contexto
- [x] Cliente MCP genérico — acoplar un agente a cualquier host MCP sin
  código nuevo
- [x] RAG reactivado con embeddings multilingües + bloqueo de
  `search_web`/`fetch_url` a nivel de código cuando el RAG ya tiene contexto
  (evita que el LLM busque en la web lo que ya tiene indexado)
- [x] Pipeline de ingesta de normativa desde SUIN-Juriscol + códigos legales
  completos (civil, penal, laboral, familia, comercial, administrativo,
  tributario)

---

## 🧹 Sprint 11 — Lo que falta de verdad para cerrar el proyecto

Esta es la lista completa, consolidada de todo lo anterior. Todo lo demás que
alguna vez apareció como pendiente en v2.0 ya está hecho.

- [ ] **Decisión de producto + limpieza de docs**: retirar formalmente
  `desktop/` (Tauri, sin commits desde 2026-07-18, nunca en el flujo real de
  arranque) y reescribir `APP.md`/`EXPORT.md` para que describan la
  distribución real (venv + NSSM), no la app nativa que no se construyó.
  *Recomendación: retirar — es el camino en el que ya se invirtió esfuerzo real.*
- [ ] Export: `update` in-place preservando memoria/config del agente
- [ ] Export: `rollback` a versión anterior
- [ ] Adjuntos: soporte de **imágenes (vision/OCR) y audio (transcripción)**
  — el resto de formatos (texto, PDF, DOCX, XLSX, CSV) ya funciona
- [ ] Test dedicado de aislamiento cross-agente del sandbox
- [ ] Frontend: responsive + estados loading/empty/error
- [ ] Verificar `install.sh` en una Mac/Linux real (ver Sprint 7/9 —
  arreglado por código hoy, falta la corrida real)
- [ ] Equivalente a NSSM para macOS (`launchd` + `.plist`) si se quiere que
  el Hub corra como servicio ahí también, no solo `bash Iniciar-R2Hub.sh` manual
- [ ] Frontend: campo de `channels.telegram.{bot_token,allowed_users}` en el
  wizard/`AgentDetail` (hoy funciona pero requiere editar `config.yaml` a mano)
- [x] **`hub/requirements.txt` — pins arreglados (2026-08-05).** Estaban
  desalineados de lo realmente instalado (`pydantic==2.8.2` pedido vs
  `2.14.0a1` corriendo de verdad) y las versiones viejas no tienen wheel
  para Python 3.14, forzando una compilación de `pydantic-core` desde
  código fuente que fallaba acá (política de Application Control). Todos
  los pins exactos actualizados a lo que de verdad corre y está probado en
  esta máquina; `chromadb`/`sentence-transformers`/`mcp` quedan como estaban
  (`>=`, nunca estuvieron desalineados). `pydantic==2.14.0a1` es a
  propósito una prerelease — no existe todavía una 2.x estable con wheel
  cp314; el comentario en el archivo lo explica. **Verificado con una
  instalación real desde cero** (venv nuevo, no solo "ya estaba
  satisfecho"): descarga, instala e importa todo sin compilar nada.

---

## 🔄 Roadmap Post-MVP (sin cambios respecto a v2.0 — visión futura, no en desarrollo)

```text
v2.1 — Comunicación entre agentes
  → Hub como router de mensajes entre agentes
  → "R2 PRIME, pídele a Legal que revise este contrato"

v2.2 — Pool compartido de LLMs
  → Los agentes no cargan su propio modelo
  → El Hub asigna modelos según demanda
  → Ahorra RAM: 1 modelo en RAM en vez de N

v2.3 — Plugin Store
  → Tools descargables desde GitHub
  → Instalar tools de terceros por agente

v2.4 — Modo multiusuario
  → Cada usuario ve solo sus agentes
  → Login, auth, roles
```
