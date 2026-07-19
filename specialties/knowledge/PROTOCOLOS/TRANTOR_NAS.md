# 🗄️ Protocolo: Acceso a Trantor NAS

> Prioridad: 🟡 MEDIA
> Última revisión: 2026-07-03

## Propósito
Acceder a los discos de Trantor (DiscoE, DiscoC) desde Coruscant.

## Conexiones disponibles

| Método | Estado | Uso |
|---|---|---|
| SMB mount `~/Trantor/DiscoE/` | ⚠️ Montado, CLI bloqueado por macOS | Finder OK, scripts NO |
| SSH `ssh trantor` | ✅ Funcional | Comandos shell, SCP |
| Tailscale | ✅ Las 3 máquinas conectadas | Red segura entre equipos |

## SMB macOS — Problema conocido
- **Síntoma:** `ls ~/Trantor/DiscoE/` → "Operation not permitted"
- **Causa:** macOS Ventura 13.7.8 restringe enumeración de directorios en monturas smbfs desde CLI
- **Afecta:** `ls`, `find`, `python listdir/open`, lectura de archivos por script
- **No afecta:** `stat`, `cat` (con ruta exacta), Finder

## Soluciones disponibles
1. **SSH/SCP** — Funcional, usar para scripts y transferencias
   ```bash
   ssh trantor "dir E:\..."
   scp trantor:"E:\ruta\archivo" ~/destino/
   ```
2. **SMB desde Terminus** — Linux no tiene restricciones SMB
3. **NFS (futuro)** — Podría reemplazar SMB si se configura en Trantor

## Datos de conexión
- **IP:** 192.168.0.23 | **Tailscale:** 100.114.207.109
- **SMB user:** smbuser / pass: 2368
- **SSH:** usuario xavier, password 2368
