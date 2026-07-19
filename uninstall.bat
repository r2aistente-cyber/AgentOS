@echo off
setlocal EnableDelayedExpansion
title R2 Hub / AgentOS — Desinstalador

echo.
echo  ============================================================
echo    R2 Hub / AgentOS — Desinstalador Windows
echo  ============================================================
echo.
echo  AVISO: Este script puede eliminar datos de agentes y el venv.
echo  Lee cada opcion con cuidado.
echo.

set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
set "VENV=%REPO%\backend\.venv"
set "AGENTOS_HOME=%USERPROFILE%\AgentOS"
set "DESKTOP=%USERPROFILE%\Desktop"

:: ── Detener Hub si corre ────────────────────────────────────────────────────
echo [1/4] Deteniendo R2 Hub si esta corriendo...
taskkill /f /im "python.exe" /fi "WINDOWTITLE eq R2 Hub*" >nul 2>&1
:: Tambien matar cualquier uvicorn en el puerto 8234
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8234 "') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo  [OK] Hub detenido (si estaba corriendo)

:: ── Acceso directo ──────────────────────────────────────────────────────────
echo [2/4] Eliminando acceso directo del escritorio...
if exist "%DESKTOP%\R2 Hub.lnk" (
    del "%DESKTOP%\R2 Hub.lnk"
    echo  [OK] Acceso directo eliminado
) else (
    echo  [--] No se encontro acceso directo
)

:: ── Virtualenv ──────────────────────────────────────────────────────────────
echo [3/4] Virtualenv de Python...
if exist "%VENV%" (
    set /p "DEL_VENV=  Eliminar el entorno virtual (%VENV%)? [s/N]: "
    if /i "!DEL_VENV!" equ "s" (
        rmdir /s /q "%VENV%"
        echo   [OK] Virtualenv eliminado
    ) else (
        echo   [--] Virtualenv conservado
    )
) else (
    echo  [--] Virtualenv no encontrado
)

:: ── AgentOS data ─────────────────────────────────────────────────────────────
echo [4/4] Datos de AgentOS (~\AgentOS)...
if exist "%AGENTOS_HOME%" (
    echo.
    echo  ADVERTENCIA: Esto eliminara TODOS tus agentes, memorias y datos.
    echo  Directorio: %AGENTOS_HOME%
    echo.
    set /p "DEL_DATA=  Eliminar TODOS los datos de agentes? [s/N]: "
    if /i "!DEL_DATA!" equ "s" (
        set /p "CONFIRM=  Escribe CONFIRMAR para continuar: "
        if "!CONFIRM!" equ "CONFIRMAR" (
            rmdir /s /q "%AGENTOS_HOME%"
            echo   [OK] Datos de AgentOS eliminados
        ) else (
            echo   [--] Confirmacion incorrecta — datos conservados
        )
    ) else (
        echo   [--] Datos de agentes conservados en %AGENTOS_HOME%
    )
) else (
    echo  [--] Directorio AgentOS no encontrado
)

echo.
echo  ============================================================
echo    Desinstalacion completada
echo  ============================================================
echo.
echo  Los archivos del repositorio en %REPO% NO fueron eliminados.
echo  Para borrar el repositorio: rmdir /s /q "%REPO%"
echo.
pause
endlocal
