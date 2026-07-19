# 💰 Protocolo: Pagos

> Prioridad: 🔴 ALTA
> Última revisión: 2026-07-03

## Propósito
Gestionar los pagos mensuales: registro, recordatorios, sincronización.

---

## 📌 REGLAS DE ORO

### R-01: Registrar inmediatamente
Cuando alguien (Xavier o Luisa) diga "pago X está pagado":
- **REGISTRAR EN EL EXCEL INMEDIATAMENTE** en ese mismo mensaje
- No esperar, no asentir, no preguntar después
- Usar: `python3 recordatorios_pagos_mac.py --marcar "Concepto"`

### R-02: Sincronizar después de cada cambio
Después de MODIFICAR el Excel:
- El script `recordatorios_pagos_mac.py` ya incluye `sync_excel_back()` que:
  1. Copia el Excel local → Trantor vía SCP
  2. Trantor lo mueve a `G:\My Drive\Control de Pagos.xlsx` vía PowerShell
- **No requiere acción manual.** Ocurre automáticamente al marcar.

### R-03: Archivo siempre actualizado
- Antes de LEER o MODIFICAR el Excel, el script trae la última versión:
  ```
  scp trantor:"G:/My Drive/Control de Pagos.xlsx" ~/.openclaw/workspace/
  ```
- **Nunca trabaja con datos en caché.**

### R-04: Verificar antes de cada recordatorio
Antes de enviar recordatorio (8am / 6pm):
- Leer el Excel fresco desde Trantor (R-03)
- Verificar fechas como datetime, no strings
- Leer NOTAS del Cronograma (pagos bimensuales, etc.)
- Validar que no haya duplicados en la hoja Pagos

### R-05: Pagos vencidos se recuerdan diario
Si pago tiene fecha ≤ hoy y NO está marcado Pagado:
- 🔴 **VENCIDO** — incluir días de retraso
- Seguir recordando TODOS LOS DÍAS hasta que se marque pagado

### R-06: Un día antes también se recuerda
Si mañana vence un pago:
- ⚠️ **VENCE MAÑANA**
- Incluir en recordatorio del día anterior

---

## 📊 Estructura del Excel

### Hoja: Cronograma — Pagos programados

| Col | Campo | Descripción | Ejemplo |
|---|---|---|---|
| A | Día | Día del mes en que vence | 1, 5, 10, 15, 23, 25, 26 |
| B | Concepto | Nombre del pago | Pensión Juan, TC Mabel |
| C | Monto | Valor en pesos colombianos | 150000, 1550000 |
| D | Responsable | Quién paga | Xavier o Luisa |
| E | Referencia de pago | Número de ref. o convenio | 1703, 63658268, 12653414 |
| F | Nota | URLs, instrucciones especiales | Links a portales de pago |

### Hoja: Pagos — Historial de lo pagado

| Col | Campo | Descripción | Ejemplo |
|---|---|---|---|
| A | Fecha | Fecha en que se pagó | 2026-07-03 |
| B | Concepto | Nombre del pago | TC Mabel |
| C | Monto | Valor | 150000 |
| D | Responsable | Quién pagó | Xavier |
| E | Estado | Pagado / pendiente | Pagado |

### Pagos registrados en Cronograma

| Día | Concepto | Monto | Responsable |
|---|---|---|---|
| 1 | TC Mabel | $150.000 | Xavier |
| 1 | Pasajes Xavier | $80.000 | Xavier |
| 1 | Mercado | $1.600.000 | Luisa |
| 1 | Pasajes Luisa | $48.000 | Luisa |
| 1 | Gasolina | $130.000 | Luisa |
| 5 | Pensión Juan | $1.550.000 | Xavier |
| 1 | Cuota Davivienda Xavier | $850.000 | Xavier |
| 5 | Claro Luisa | $50.000 | Luisa |
| 5 | Plataformas (Streaming) | $83.000 | Luisa |
| 10 | Administración | $418.000 | Xavier |
| 10 | Vanti (gas) | $150.000 | Xavier |
| 10 | Codensa (energía) | $150.000 | Xavier |
| 15 | Claro Xavier | $60.000 | Xavier |
| 23 | María Camila | $650.000 | Luisa |
| 23 | Ahorro | $1.500.000 | Luisa |
| 23 | Contingencias | $500.000 | Luisa |
| 23 | Acueducto | $260.000 | Xavier |
| 25 | ETB (internet) | $135.000 | Luisa |
| 26 | Crédito Hipotecario | $1.500.000 | Luisa |

### Reglas especiales por pago

| Pago | Regla |
|---|---|
| **Acueducto** | Bimestral. Solo notificar en jul, sep, nov, ene, mar, may. Referencia: 12653414. Pagar desde Mac de Luisa. |
| **Pensión Juan** | Referencia: 1703. Pagar en zonapagos.com. |
| **Administración** | Pagar en avalpaycenter.com. |
| **Vanti (gas)** | Referencia: 63658268. Pagar en grupovanti.com. |
| **Codensa (energía)** | Referencia: 7719970-7. Pagar desde Mac de Luisa. |
| **ETB (internet)** | Referencia: 12054954469. |
| **Acueducto** | Pagar desde Mac de Luisa. |

---

## ⚙️ Stack técnico

| Componente | Detalle |
|---|---|
| Script principal | `recordatorios_pagos_mac.py` (Python 3 + openpyxl) |
| Excel Drive (Coruscant) | `gdrive:R2-Mac/Control de Pagos.xlsx` (vía rclone — fuente de verdad) |
| Excel local | `~/.openclaw/workspace/Control de Pagos.xlsx` |
| Sincronización | `rclone copy` bidireccional (Drive es read-only desde la CLI de macOS) |
| Envío WhatsApp | `openclaw agent --deliver` |
| Schedule | launchd (`com.r2.recordatorios.pagos`) a las 8:00 y 18:00 hora Bogotá |
| Modelo | **No usa LLM.** El script es puro Python + datos. Llamadas a `openclaw agent --deliver` directas. |

## 📋 Formato de recordatorio

```
📋 Recordatorio de Pagos - DD/MM

🔴 VENCIDOS:
• Concepto — $Monto — Resp — VENCE hace X días

⚠️ VENCE MAÑANA:
• Concepto — $Monto — Resp

✅ Pagados este mes:
• Concepto — $Monto — Resp ✔️

💰 Total pendiente: $XXX.XXX
```

---

## ⚠️ Manejo de errores

### E-01: Google Drive no accesible
1. Usar copia local existente (puede estar desactualizada)
2. Notificar: "No pude sincronizar con Drive — usando copia local"

### E-04: Bug corregido — sobrescritura del Excel
- **Causa:** El Drive montado en macOS es read-only desde CLI. `cp` desde Drive a local siempre funcionaba, pero `cp` inverso fallaba silenciosamente. Cada ejecución de `find_excel()` copiaba la versión obsoleta de Drive sobre la local, borrando pagos marcados.
- **Solución:** Reemplazar `cp` por `rclone copy` para ambas direcciones. `sync_to_drive()` y `sync_from_drive()` usan rclone, que sí puede escribir en Drive.
- **Fecha:** 2026-07-07

### E-05: Bug corregido — rclone timeout 15s borraba pagos marcados
- **Causa:** `_rclone()` tenía timeout de 15s para copiar a Google Drive. Con conexiones lentas, el timeout se disparaba antes de completar la subida. El siguiente `sync_from_drive()` traía la versión vieja de Drive, pisando los cambios locales (pagos marcados se perdían).
- **Solución:** Timeout de `_rclone()` aumentado de 15s → 60s
- **Fecha:** 2026-07-10
- **Nota:** Verificar periódicamente que rclone no esté dando timeouts.

### E-02: Excel dañado o no encontrado
1. Reintentar SCP
2. Si no existe local ni remoto: NOTIFICAR
3. NO inventar datos ni usar valores en caché

### E-03: OpenClaw agent no responde
1. Registrar en `error_log.json`
2. Reintentar 1 minuto después
3. Si persiste: notificar que no se pudo entregar

### Error log
`~/.openclaw/workspace/error_log.json`

---

## Notas
- Sincronización Drive vía SCP+PowerShell es workaround por cloud-only de macOS.
- Script **no depende del modelo de IA**. Corre en Python puro.
- Si en futuro se resuelve el acceso directo a Drive, actualizar protocolo.
