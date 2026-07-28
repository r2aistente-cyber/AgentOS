<#
Instala Hub y mcp_gateway como servicios de Windows via NSSM, con reinicio
automatico ante caida y arranque automatico al prender el equipo.

Requiere PowerShell elevada (clic derecho > Ejecutar como administrador) --
`nssm install` escribe en HKLM y falla/cuelga sin permisos de admin.

r2-legal (el agente) NO se registra aca a proposito: ya lo supervisa el
propio Hub via AgentManager (healthcheck + auto_restart en agents.json) una
vez que el Hub mismo esta corriendo de forma confiable. Registrarlo tambien
como servicio NSSM competiria con esa logica (el mismo tipo de bug de
"proceso duplicado" que ya se corrigio en el Hub el 2026-07-24).

Uso:
    powershell -ExecutionPolicy Bypass -File Instalar-Servicios-NSSM.ps1
#>

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Este script necesita PowerShell elevada (Ejecutar como administrador). Abortando."
    exit 1
}

$nssm = "C:\Users\xavier\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe"
if (-not (Test-Path $nssm)) {
    Write-Error "No se encontro nssm.exe en $nssm -- revisa que 'winget install NSSM.NSSM' haya terminado bien."
    exit 1
}

$logDir = "C:\Users\xavier\AgentOS\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

# ─── R2Hub ────────────────────────────────────────────────────────────────
$hubPython = "C:\Users\xavier\.openclaw\workspace\r2-autonomous\backend\.venv\Scripts\python.exe"
$hubDir    = "C:\Users\xavier\.openclaw\workspace\r2-autonomous"

if (Get-Service -Name R2Hub -ErrorAction SilentlyContinue) {
    Write-Output "El servicio R2Hub ya existe -- se omite instalacion (usa 'nssm remove R2Hub confirm' primero si quieres recrearlo)."
} else {
    & $nssm install R2Hub $hubPython "-m hub.main"
    & $nssm set R2Hub AppDirectory $hubDir
    & $nssm set R2Hub DisplayName "R2 Hub (AgentOS)"
    & $nssm set R2Hub Description "FastAPI Hub que administra los agentes de AgentOS (r2-legal, etc.)"
    & $nssm set R2Hub Start SERVICE_AUTO_START
    & $nssm set R2Hub AppExit Default Restart
    & $nssm set R2Hub AppRestartDelay 3000
    & $nssm set R2Hub AppStdout "$logDir\R2Hub.service.out.log"
    & $nssm set R2Hub AppStderr "$logDir\R2Hub.service.err.log"
    & $nssm set R2Hub AppRotateFiles 1
    & $nssm set R2Hub AppRotateBytes 5242880
    Write-Output "Servicio R2Hub creado."
}

# ─── SuiteLegalMCPGateway ───────────────────────────────────────────────────
$mcpPython = "C:\Users\xavier\.openclaw\workspace\suite-legal\mcp_gateway\.venv\Scripts\python.exe"
$mcpDir    = "C:\Users\xavier\.openclaw\workspace\suite-legal\mcp_gateway"

# Misma API key que ya usa r2-legal para llamar al gateway. Se lee en vivo
# desde su config.yaml (fuente de verdad, mcp_servers[].api_key) en vez de
# hardcodearla aca -- este script se commitea al repo, y un secreto en
# texto plano en git es exactamente el tipo de leak que se cerro en la
# auditoria de API keys (ver commit 366ee86 de suite-legal). Antes la key
# vivia solo en la memoria de quien arrancaba el proceso a mano; ahora
# queda en el registro del servicio (HKLM, requiere admin para leerlo).
$r2LegalConfigPath = "C:\Users\xavier\AgentOS\agents\r2-legal\config.yaml"
if (-not (Test-Path $r2LegalConfigPath)) {
    Write-Error "No se encontro $r2LegalConfigPath -- no se puede leer la API key del MCP gateway."
    exit 1
}
$mcpApiKeyLine = Select-String -Path $r2LegalConfigPath -Pattern '^\s*api_key:\s*(\S+)' -AllMatches |
    Where-Object { $_.LineNumber -gt (Select-String -Path $r2LegalConfigPath -Pattern '^mcp_servers:').LineNumber } |
    Select-Object -First 1
if (-not $mcpApiKeyLine) {
    Write-Error "No se pudo extraer mcp_servers[].api_key de $r2LegalConfigPath -- revisa el formato del archivo."
    exit 1
}
$suiteLegalApiKey = $mcpApiKeyLine.Matches[0].Groups[1].Value

if (Get-Service -Name SuiteLegalMCPGateway -ErrorAction SilentlyContinue) {
    Write-Output "El servicio SuiteLegalMCPGateway ya existe -- se omite instalacion."
} else {
    & $nssm install SuiteLegalMCPGateway $mcpPython "server.py"
    & $nssm set SuiteLegalMCPGateway AppDirectory $mcpDir
    & $nssm set SuiteLegalMCPGateway DisplayName "Suite Legal - MCP Gateway"
    & $nssm set SuiteLegalMCPGateway Description "Expone Suite Legal como servidor MCP para agentes de IA (puerto 8010)"
    & $nssm set SuiteLegalMCPGateway Start SERVICE_AUTO_START
    & $nssm set SuiteLegalMCPGateway AppExit Default Restart
    & $nssm set SuiteLegalMCPGateway AppRestartDelay 3000
    & $nssm set SuiteLegalMCPGateway AppEnvironmentExtra "SUITE_LEGAL_API_KEY=$suiteLegalApiKey"
    & $nssm set SuiteLegalMCPGateway AppStdout "$logDir\SuiteLegalMCPGateway.service.out.log"
    & $nssm set SuiteLegalMCPGateway AppStderr "$logDir\SuiteLegalMCPGateway.service.err.log"
    & $nssm set SuiteLegalMCPGateway AppRotateFiles 1
    & $nssm set SuiteLegalMCPGateway AppRotateBytes 5242880
    Write-Output "Servicio SuiteLegalMCPGateway creado."
}

# ─── Cuenta bajo la cual corren los servicios ──────────────────────────────
# NSSM instala por defecto como LocalSystem. Bajo esa cuenta,
# os.path.expanduser("~") (hub/config.py::home_dir, usado para
# ~/AgentOS/agents.json) resuelve al perfil de sistema
# (C:\Windows\System32\config\systemprofile), no a C:\Users\xavier -- el
# servicio queda "Running" pero el Hub arranca viendo 0 agentes en el
# registro (bug real encontrado el 2026-07-28 al instalar por primera vez:
# agents.json de xavier invisible para el servicio). Corremos ambos
# servicios como xavier para que ~ resuelva donde corresponde.
Write-Output ""
$cred = Get-Credential -UserName "$env:COMPUTERNAME\xavier" -Message "Contrasena de Windows de xavier (para que R2Hub/SuiteLegalMCPGateway corran como xavier, no LocalSystem)"
$plainPassword = $cred.GetNetworkCredential().Password
$objectName = $cred.UserName
foreach ($svc in @("R2Hub", "SuiteLegalMCPGateway")) {
    if ((Get-Service -Name $svc -ErrorAction SilentlyContinue).Status -eq "Running") {
        Stop-Service $svc
    }
    & $nssm set $svc ObjectName $objectName $plainPassword
}
$plainPassword = $null

Write-Output ""
Write-Output "Arrancando servicios..."
Start-Service R2Hub
Start-Service SuiteLegalMCPGateway
Start-Sleep -Seconds 3
Get-Service R2Hub, SuiteLegalMCPGateway | Format-Table Name, Status, StartType

Write-Output ""
Write-Output "Nota: SuiteLegalMCPGateway depende de que Suite Legal backend (puerto 8000)"
Write-Output "este corriendo -- si no lo esta, el servicio queda vivo pero guardar_borrador"
Write-Output "fallara con 'no se pudo conectar' hasta que arranques el backend."
