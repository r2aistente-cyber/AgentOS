<#
Revierte lo que hace Instalar-Servicios-NSSM.ps1: detiene y elimina los
servicios R2Hub y SuiteLegalMCPGateway. Requiere PowerShell elevada.
#>

$ErrorActionPreference = "Continue"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Este script necesita PowerShell elevada (Ejecutar como administrador). Abortando."
    exit 1
}

$nssm = "C:\Users\xavier\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe"

foreach ($svc in @("R2Hub", "SuiteLegalMCPGateway")) {
    if (Get-Service -Name $svc -ErrorAction SilentlyContinue) {
        Stop-Service $svc -Force -ErrorAction SilentlyContinue
        & $nssm remove $svc confirm
        Write-Output "Servicio $svc eliminado."
    } else {
        Write-Output "Servicio $svc no existia."
    }
}
