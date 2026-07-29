<#
Instala servicios de Windows via NSSM, con reinicio automatico ante caida
y arranque automatico al prender el equipo. Sirve tanto para la
instalacion base de Suite Legal (solo SuiteLegalBackend, sin IA) como
para acoplar la IA despues (R2Hub + SuiteLegalMCPGateway) -- ver
suite-legal/docs/INSTALACION-DESPACHO.md y ACOPLAR-IA.md.

Requiere PowerShell elevada (clic derecho > Ejecutar como administrador) --
`nssm install` escribe en HKLM y falla/cuelga sin permisos de admin.

r2-legal (el agente) NO se registra aca a proposito: ya lo supervisa el
propio Hub via AgentManager (healthcheck + auto_restart en agents.json) una
vez que el Hub mismo esta corriendo de forma confiable. Registrarlo tambien
como servicio NSSM competiria con esa logica (el mismo tipo de bug de
"proceso duplicado" que ya se corrigio en el Hub el 2026-07-24).

Es idempotente: si un servicio ya existe, se omite su instalacion (no lo
recrea, no le vuelve a pedir credenciales) -- seguro de re-correr para
agregar servicios que faltan sin tocar los que ya estan.

Uso (todos los servicios, comportamiento historico):
    powershell -ExecutionPolicy Bypass -File Instalar-Servicios-NSSM.ps1

Uso (solo el backend de Suite Legal, instalacion sin IA):
    powershell -ExecutionPolicy Bypass -File Instalar-Servicios-NSSM.ps1 -Servicios SuiteLegalBackend

Uso (acoplar IA sobre una instalacion que ya tiene SuiteLegalBackend):
    powershell -ExecutionPolicy Bypass -File Instalar-Servicios-NSSM.ps1 -Servicios R2Hub,SuiteLegalMCPGateway

Uso en una maquina distinta a la de Xavier (otro despacho):
    powershell -ExecutionPolicy Bypass -File Instalar-Servicios-NSSM.ps1 `
        -Servicios SuiteLegalBackend `
        -SuiteLegalDir "D:\SuiteLegal" `
        -ServiceAccount ".\despacho_svc"
#>

param(
    # Cuales de los 3 servicios instalar/asegurar en esta corrida.
    [ValidateSet("R2Hub", "SuiteLegalMCPGateway", "SuiteLegalBackend")]
    [string[]]$Servicios = @("R2Hub", "SuiteLegalMCPGateway", "SuiteLegalBackend"),

    [string]$R2AutonomousDir = "C:\Users\xavier\.openclaw\workspace\r2-autonomous",
    [string]$SuiteLegalDir   = "C:\Users\xavier\.openclaw\workspace\suite-legal",
    [string]$AgentOSDir      = (Join-Path $env:USERPROFILE "AgentOS"),
    [string]$NssmPath        = "C:\Users\xavier\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe",

    # Cuenta bajo la que corren los servicios que se instalen en esta
    # corrida. NSSM instala por defecto como LocalSystem, pero el Hub
    # resuelve ~/AgentOS via os.path.expanduser("~") -- bajo LocalSystem
    # eso apunta al perfil de sistema, no al del usuario real, y el Hub
    # arranca viendo 0 agentes en el registro aunque el servicio este
    # "Running" (bug real encontrado el 2026-07-28). Por default se pide
    # por credencial interactiva; para no pedirla en cada corrida (ej.
    # scripts encadenados), pasar -ServiceAccount y -ServiceAccountPassword.
    [string]$ServiceAccount,
    [securestring]$ServiceAccountPassword
)

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Este script necesita PowerShell elevada (Ejecutar como administrador). Abortando."
    exit 1
}

if (-not (Test-Path $NssmPath)) {
    Write-Error "No se encontro nssm.exe en $NssmPath -- revisa que 'winget install NSSM.NSSM' haya terminado bien (o pasa -NssmPath)."
    exit 1
}
$nssm = $NssmPath

$logDir = Join-Path $AgentOSDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$serviciosInstaladosAhora = @()

# ─── R2Hub ────────────────────────────────────────────────────────────────
if ($Servicios -contains "R2Hub") {
    $hubPython = Join-Path $R2AutonomousDir "backend\.venv\Scripts\python.exe"
    $hubDir    = $R2AutonomousDir

    if (Get-Service -Name R2Hub -ErrorAction SilentlyContinue) {
        Write-Output "El servicio R2Hub ya existe -- se omite instalacion (usa 'nssm remove R2Hub confirm' primero si queres recrearlo)."
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
        $serviciosInstaladosAhora += "R2Hub"
    }
}

# ─── SuiteLegalMCPGateway ───────────────────────────────────────────────────
if ($Servicios -contains "SuiteLegalMCPGateway") {
    $mcpPython = Join-Path $SuiteLegalDir "mcp_gateway\.venv\Scripts\python.exe"
    $mcpDir    = Join-Path $SuiteLegalDir "mcp_gateway"

    # Misma API key que ya usa r2-legal para llamar al gateway. Se lee en vivo
    # desde su config.yaml (fuente de verdad, mcp_servers[].api_key) en vez de
    # hardcodearla aca -- este script se commitea al repo, y un secreto en
    # texto plano en git es exactamente el tipo de leak que se cerro en la
    # auditoria de API keys (ver commit 366ee86 de suite-legal).
    $r2LegalConfigPath = Join-Path $AgentOSDir "agents\r2-legal\config.yaml"
    if (-not (Test-Path $r2LegalConfigPath)) {
        Write-Error "No se encontro $r2LegalConfigPath -- corre primero el acople de IA (crea el agente r2-legal) antes de registrar SuiteLegalMCPGateway."
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
        $serviciosInstaladosAhora += "SuiteLegalMCPGateway"
    }
}

# ─── SuiteLegalBackend ──────────────────────────────────────────────────────
if ($Servicios -contains "SuiteLegalBackend") {
    $backendPython = Join-Path $SuiteLegalDir "backend\.venv\Scripts\python.exe"
    $backendDir    = Join-Path $SuiteLegalDir "backend"

    if (Get-Service -Name SuiteLegalBackend -ErrorAction SilentlyContinue) {
        Write-Output "El servicio SuiteLegalBackend ya existe -- se omite instalacion."
    } else {
        & $nssm install SuiteLegalBackend $backendPython "-m uvicorn app.main:app --host 127.0.0.1 --port 8000"
        & $nssm set SuiteLegalBackend AppDirectory $backendDir
        & $nssm set SuiteLegalBackend DisplayName "Suite Legal - Backend"
        & $nssm set SuiteLegalBackend Description "API + frontend (si fue buildeado) de Suite Legal (puerto 8000)"
        & $nssm set SuiteLegalBackend Start SERVICE_AUTO_START
        & $nssm set SuiteLegalBackend AppExit Default Restart
        & $nssm set SuiteLegalBackend AppRestartDelay 3000
        & $nssm set SuiteLegalBackend AppStdout "$logDir\SuiteLegalBackend.service.out.log"
        & $nssm set SuiteLegalBackend AppStderr "$logDir\SuiteLegalBackend.service.err.log"
        & $nssm set SuiteLegalBackend AppRotateFiles 1
        & $nssm set SuiteLegalBackend AppRotateBytes 5242880
        Write-Output "Servicio SuiteLegalBackend creado."
        $serviciosInstaladosAhora += "SuiteLegalBackend"
    }
}

if ($serviciosInstaladosAhora.Count -eq 0) {
    Write-Output ""
    Write-Output "Ningun servicio nuevo que instalar (todos los pedidos ya existian). Nada que arrancar."
    exit 0
}

# ─── Cuenta bajo la cual corren los servicios recien creados ───────────────
Write-Output ""
if ($ServiceAccount -and $ServiceAccountPassword) {
    $objectName = $ServiceAccount
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($ServiceAccountPassword))
} else {
    $cred = Get-Credential -UserName "$env:COMPUTERNAME\$env:USERNAME" -Message "Contrasena de Windows de la cuenta bajo la que van a correr: $($serviciosInstaladosAhora -join ', ')"
    $objectName = $cred.UserName
    $plainPassword = $cred.GetNetworkCredential().Password
}
foreach ($svc in $serviciosInstaladosAhora) {
    & $nssm set $svc ObjectName $objectName $plainPassword
}
$plainPassword = $null

Write-Output ""
Write-Output "Arrancando servicios nuevos..."
foreach ($svc in $serviciosInstaladosAhora) {
    Start-Service $svc
}
Start-Sleep -Seconds 3
Get-Service $Servicios | Format-Table Name, Status, StartType

if ($Servicios -contains "SuiteLegalMCPGateway") {
    Write-Output ""
    Write-Output "Nota: SuiteLegalMCPGateway depende de que Suite Legal backend (puerto 8000)"
    Write-Output "este corriendo -- si no lo esta, el servicio queda vivo pero guardar_borrador"
    Write-Output "fallara con 'no se pudo conectar' hasta que arranques el backend."
}
