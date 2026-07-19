#!/usr/bin/env bash
# R2 Hub / AgentOS — Desinstalador macOS/Linux
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO/backend/.venv"
AGENTOS_HOME="$HOME/AgentOS"

echo ""
echo "============================================================"
echo "  R2 Hub / AgentOS — Desinstalador"
echo "============================================================"
echo ""
echo "  AVISO: Este script puede eliminar datos de agentes y el venv."
echo "  Lee cada opcion con cuidado."
echo ""

# ── Detener Hub si corre ─────────────────────────────────────────────────────
echo "[1/4] Deteniendo R2 Hub si esta corriendo..."
# Matar proceso uvicorn en puerto 8234
if command -v lsof &>/dev/null; then
    PID=$(lsof -ti :8234 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null && echo "  [OK] Hub detenido (PID $PID)"
    else
        echo "  [--] Hub no estaba corriendo"
    fi
else
    echo "  [--] lsof no disponible, Hub no verificado"
fi

# ── Acceso directo macOS ─────────────────────────────────────────────────────
echo "[2/4] Eliminando launcher del escritorio..."
DESKTOP_CMD="$HOME/Desktop/R2 Hub.command"
if [ -f "$DESKTOP_CMD" ]; then
    rm "$DESKTOP_CMD"
    echo "  [OK] Launcher eliminado"
else
    echo "  [--] Launcher no encontrado"
fi

# ── Virtualenv ───────────────────────────────────────────────────────────────
echo "[3/4] Virtualenv de Python..."
if [ -d "$VENV" ]; then
    read -rp "  Eliminar el entorno virtual ($VENV)? [s/N]: " DEL_VENV
    if [[ "${DEL_VENV,,}" == "s" ]]; then
        rm -rf "$VENV"
        echo "  [OK] Virtualenv eliminado"
    else
        echo "  [--] Virtualenv conservado"
    fi
else
    echo "  [--] Virtualenv no encontrado"
fi

# ── AgentOS data ─────────────────────────────────────────────────────────────
echo "[4/4] Datos de AgentOS (~/$AGENTOS_HOME)..."
if [ -d "$AGENTOS_HOME" ]; then
    echo ""
    echo "  ADVERTENCIA: Esto eliminara TODOS tus agentes, memorias y datos."
    echo "  Directorio: $AGENTOS_HOME"
    echo ""
    read -rp "  Eliminar TODOS los datos de agentes? [s/N]: " DEL_DATA
    if [[ "${DEL_DATA,,}" == "s" ]]; then
        read -rp "  Escribe CONFIRMAR para continuar: " CONFIRM
        if [[ "$CONFIRM" == "CONFIRMAR" ]]; then
            rm -rf "$AGENTOS_HOME"
            echo "  [OK] Datos de AgentOS eliminados"
        else
            echo "  [--] Confirmacion incorrecta — datos conservados"
        fi
    else
        echo "  [--] Datos de agentes conservados en $AGENTOS_HOME"
    fi
else
    echo "  [--] Directorio AgentOS no encontrado"
fi

echo ""
echo "============================================================"
echo "  Desinstalacion completada"
echo "============================================================"
echo ""
echo "  Los archivos del repositorio en $REPO NO fueron eliminados."
echo "  Para borrar el repo: rm -rf \"$REPO\""
echo ""
