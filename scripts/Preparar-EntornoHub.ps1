<#
Prepara el entorno Python del propio Hub de AgentOS (venv + dependencias
de hub/requirements.txt) -- lo que install.bat ya hace en los pasos
[3/6] para una instalación "de escritorio" completa (agente R2-PRIME +
acceso directo incluidos). Este script solo extrae esa parte: hace falta
como paso previo a acoplar un agente vía Acoplar-IA.ps1 en una máquina
de despacho nueva, donde nada de eso existe todavía -- install.bat en sí
no se reusa porque también crea R2-PRIME y un acceso directo de
escritorio, que no aplican a un Hub corriendo como servicio de Windows.

Idempotente: si el venv ya existe, no lo recrea (mismo patrón que el
resto de los instaladores de esta sesión).

Uso:
    powershell -ExecutionPolicy Bypass -File Preparar-EntornoHub.ps1
#>

param(
    [string]$R2AutonomousDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

function Confirmar-ExitCode([string]$Descripcion) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Descripcion fallo (exit $LASTEXITCODE)"
    }
}

$venvDir    = Join-Path $R2AutonomousDir "backend\.venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

Write-Output "=== Preparando el entorno del Hub ==="
if (-not (Test-Path $venvPython)) {
    python -m venv $venvDir
    Confirmar-ExitCode "python -m venv (Hub)"
    Write-Output "Virtualenv creado en $venvDir"
} else {
    Write-Output "Virtualenv ya existe en $venvDir"
}

& $venvPython -m pip install --upgrade pip --quiet
Confirmar-ExitCode "pip install --upgrade pip (Hub)"
& $venvPython -m pip install -r (Join-Path $R2AutonomousDir "hub\requirements.txt") --quiet
Confirmar-ExitCode "pip install -r hub\requirements.txt"
Write-Output "Dependencias del Hub instaladas."
