@echo off
title R2 Hub - AgentOS
cd /d "%~dp0"
set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
set "VENV=%REPO%\.venv"
set "AGENTOS_HOME=%USERPROFILE%\AgentOS"
if not exist "%AGENTOS_HOME%\logs" mkdir "%AGENTOS_HOME%\logs"

echo.
echo  ==========================================
echo   R2 Hub / AgentOS - Iniciando...
echo  ==========================================
echo.

:: Verificar que el Hub no este ya corriendo
curl -s http://localhost:8234/ >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Hub ya esta corriendo en :8234
    goto check_vite
)

echo  [1/3] Arrancando Hub (backend)...
:: Start-Process -WindowStyle Hidden = sin consola, ni siquiera un flash
:: (a diferencia de "start /min", que sí llega a mostrarse un instante).
:: stdout/stderr van a AgentOS\logs en vez de perderse en una ventana que
:: ya no existe.
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%VENV%\Scripts\python.exe' -ArgumentList '-m','hub.main' -WorkingDirectory '%REPO%' -WindowStyle Hidden -RedirectStandardOutput '%AGENTOS_HOME%\logs\hub_stdout.log' -RedirectStandardError '%AGENTOS_HOME%\logs\hub_stderr.log'"

:: Esperar que el Hub responda
echo       Esperando Hub...
:wait_hub
timeout /t 1 /nobreak >nul
curl -s http://localhost:8234/ >nul 2>&1
if %errorlevel% neq 0 goto wait_hub
echo  [OK] Hub en linea en :8234

:check_vite
:: Verificar que Vite no este ya corriendo
curl -s http://localhost:5500/ >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Frontend ya esta corriendo en :5500
    goto launch_ui
)

echo  [2/3] Arrancando frontend (Vite)...
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm run dev' -WorkingDirectory '%REPO%\frontend' -WindowStyle Hidden -RedirectStandardOutput '%AGENTOS_HOME%\logs\frontend_stdout.log' -RedirectStandardError '%AGENTOS_HOME%\logs\frontend_stderr.log'"

:: Esperar que Vite responda
echo       Esperando frontend...
:wait_vite
timeout /t 1 /nobreak >nul
curl -s http://localhost:5500/ >nul 2>&1
if %errorlevel% neq 0 goto wait_vite
echo  [OK] Frontend en linea en :5500

:launch_ui
echo  [3/3] Abriendo ventana de escritorio...

:: Ventana nativa (pywebview) — esta SÍ debe verse, es la app en sí.
:: Corre en foreground: cuando el usuario la cierra, este script termina.
:: Hub y frontend siguen corriendo en background (ver arriba).
"%VENV%\Scripts\python.exe" "%REPO%\desktop_shell.py"
