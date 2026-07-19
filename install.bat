@echo off
setlocal EnableDelayedExpansion
title R2 Hub / AgentOS — Instalador

echo.
echo  ============================================================
echo    R2 Hub / AgentOS — Instalador Windows
echo  ============================================================
echo.

set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
set "VENV=%REPO%\backend\.venv"
set "AGENTOS_HOME=%USERPROFILE%\AgentOS"

:: ── Verificar Python 3.11+ ───────────────────────────────────────────────────
echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python no encontrado. Instala Python 3.11+ desde https://python.org
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set "PYMAJ=%%a"
    set "PYMIN=%%b"
)
if !PYMAJ! LSS 3 (
    echo  ERROR: Se requiere Python 3.11+. Tienes Python !PYVER!
    pause & exit /b 1
)
if !PYMAJ! EQU 3 if !PYMIN! LSS 11 (
    echo  ERROR: Se requiere Python 3.11+. Tienes Python !PYVER!
    pause & exit /b 1
)
echo  [OK] Python !PYVER!

:: ── Verificar Node.js 18+ ────────────────────────────────────────────────────
echo [2/6] Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  AVISO: Node.js no encontrado. WhatsApp sidecar no estara disponible.
    echo         Instala Node.js 18+ desde https://nodejs.org si lo necesitas.
) else (
    for /f %%v in ('node --version') do set "NODEVER=%%v"
    echo  [OK] Node.js !NODEVER!
)

:: ── Crear virtualenv ─────────────────────────────────────────────────────────
echo [3/6] Configurando entorno Python...
if exist "%VENV%\Scripts\python.exe" (
    echo  [OK] Virtualenv ya existe en %VENV%
) else (
    echo       Creando virtualenv...
    python -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo  ERROR: No se pudo crear el virtualenv
        pause & exit /b 1
    )
    echo  [OK] Virtualenv creado
)

echo       Instalando dependencias Python...
"%VENV%\Scripts\pip" install -r "%REPO%\hub\requirements.txt" --quiet --upgrade
if %errorlevel% neq 0 (
    echo  ERROR: Fallo al instalar dependencias Python
    pause & exit /b 1
)
echo  [OK] Dependencias instaladas

:: ── Crear estructura de directorios ─────────────────────────────────────────
echo [4/6] Creando estructura AgentOS en %AGENTOS_HOME%...
for %%d in (agents archived logs) do (
    if not exist "%AGENTOS_HOME%\%%d" mkdir "%AGENTOS_HOME%\%%d"
)
echo  [OK] Estructura creada

:: ── Crear agente R2 PRIME por defecto ───────────────────────────────────────
echo [5/6] Creando agente R2-PRIME...
"%VENV%\Scripts\python" "%REPO%\setup\create_r2_prime.py"
if %errorlevel% neq 0 (
    echo  AVISO: No se pudo crear R2-PRIME automaticamente.
    echo         Puedes crearlo desde el Hub una vez que este corriendo.
) else (
    echo  [OK] R2-PRIME listo en %AGENTOS_HOME%\agents\R2-PRIME
)

:: ── Crear acceso directo en el escritorio ───────────────────────────────────
echo [6/6] Creando acceso directo en el escritorio...
powershell -NoProfile -Command ^
  "$ws=New-Object -ComObject WScript.Shell; ^
   $s=$ws.CreateShortcut('$env:USERPROFILE\Desktop\R2 Hub.lnk'); ^
   $s.TargetPath='%REPO%\Iniciar-R2Hub.bat'; ^
   $s.WorkingDirectory='%REPO%'; ^
   $s.Description='R2 Hub / AgentOS'; ^
   $s.Save()"
echo  [OK] Acceso directo "R2 Hub" creado en el escritorio

:: ── Fin ─────────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo    Instalacion completada!
echo  ============================================================
echo.
echo    Para iniciar: doble clic en "R2 Hub" en el escritorio
echo                  o ejecuta: Iniciar-R2Hub.bat
echo.
echo    Documentacion: SPRINTS.md
echo    Agentes en:    %AGENTOS_HOME%\agents\
echo.
set /p "START=Iniciar R2 Hub ahora? [S/n]: "
if /i "!START!" neq "n" (
    echo.
    echo Iniciando R2 Hub...
    start "" "%REPO%\Iniciar-R2Hub.bat"
)
endlocal
