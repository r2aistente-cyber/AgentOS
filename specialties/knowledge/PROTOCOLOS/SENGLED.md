# 💡 Protocolo: Control de Luces Sengled

> Prioridad: 🔴 ALTA — Ejecución inmediata
> Última revisión: 2026-07-03

## Propósito
Controlar los focos inteligentes Sengled (hub E39-G8C) desde Coruscant.

## Regla de ORO
- **ÚNICO script:** `python sengled_fast.py`
- **Cero discovery, cero scripts alternativos, cero improvisación**
- **Si falla:** reportar y parar. No soluciones creativas.

## Prerequisitos
- Script en workspace: `~/workspace/sengled_fast.py`
- Config: `sengled_iids.json`, `sengled_pairing.json`
- Hub conectado: IP 192.168.0.3, HAP puerto 33734

## Comandos

| Acción | Comando | Ejemplo |
|---|---|---|
| Encender | `python sengled_fast.py on {lugar}` | `python sengled_fast.py on sala` |
| Apagar | `python sengled_fast.py off {lugar}` | `python sengled_fast.py off habitacion` |
| Brillo | `python sengled_fast.py brightness {lugar} {0-100}` | `python sengled_fast.py brightness sala 50` |
| Todo on | `python sengled_fast.py on todo` | |
| Todo off | `python sengled_fast.py off todo` | |

### Atajos de lenguaje natural
- "prende/apaga [lugar]" → comando on/off
- "brillo [lugar] [%]" → comando brightness

### Lugares válidos
- `sala` — IID 66 (brillo canal 51)
- `cocina` — IID 67 (brillo canal 51)
- `habitacion` — IID 68 (brillo canal 51 y 52)

## Notas técnicas
- Bug conocido: `put_characteristics` de aiohomekit falla buscando chars. Solución: monkey-patch en `Accessories.aid_iid`.
- Puerto HAP actual: 33734 (cambió desde el original 33425).

## Dónde aplicar
- WhatsApp: Xavier (+573192270876) y Luisa (+573192937099)
- Ambos pueden dar órdenes de luces
