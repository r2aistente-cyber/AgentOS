@echo off
title R2 Hub - AgentOS
cd /d "%~dp0"

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
start "R2-Hub Backend" /min cmd /c "backend\.venv\Scripts\python -m hub.main 2>&1"

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
start "R2-Hub Frontend" /min cmd /c "cd frontend && npm run dev 2>&1"

:: Esperar que Vite responda
echo       Esperando frontend...
:wait_vite
timeout /t 1 /nobreak >nul
curl -s http://localhost:5500/ >nul 2>&1
if %errorlevel% neq 0 goto wait_vite
echo  [OK] Frontend en linea en :5500

:launch_ui
echo  [3/3] Abriendo ventana de escritorio...
echo.
echo  ==========================================
echo   AgentOS listo. Cerrando esta ventana...
echo  ==========================================
echo.
timeout /t 2 /nobreak >nul

:: Abrir en ventana nativa (pywebview) — sin navegador
backend\.venv\Scripts\python desktop_shell.py
