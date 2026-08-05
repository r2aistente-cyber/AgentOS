#!/usr/bin/env bash
# R2 Hub / AgentOS — Lanzador macOS/Linux. Equivalente a Iniciar-R2Hub.bat:
# arranca el Hub (backend), el frontend (Vite) y la ventana nativa
# (pywebview), en ese orden, sin duplicar si ya están corriendo.
#
# Referenciado por install.sh y por el launcher que crea en el escritorio
# ($HOME/Desktop/R2 Hub.command) — antes de este archivo, ambos apuntaban
# a un script que no existía.
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO/backend/.venv"
AGENTOS_HOME="$HOME/AgentOS"
LOGS="$AGENTOS_HOME/logs"
mkdir -p "$LOGS"

echo ""
echo "=========================================="
echo "  R2 Hub / AgentOS - Iniciando..."
echo "=========================================="
echo ""

if [ ! -x "$VENV/bin/python" ]; then
    echo " ERROR: no se encontró el virtualenv en $VENV"
    echo "        Corre install.sh primero."
    exit 1
fi

wait_for() {
    # wait_for <url> <descripcion>
    local url="$1" desc="$2" tries=60
    while ! curl -s -o /dev/null "$url"; do
        tries=$((tries - 1))
        if [ "$tries" -le 0 ]; then
            echo " ERROR: $desc no respondió a tiempo ($url)"
            exit 1
        fi
        sleep 1
    done
}

# ── [1/3] Hub (backend) ────────────────────────────────────────────────────
if curl -s -o /dev/null "http://localhost:8234/"; then
    echo " [OK] Hub ya está corriendo en :8234"
else
    echo " [1/3] Arrancando Hub (backend)..."
    (cd "$REPO" && nohup "$VENV/bin/python" -m hub.main >> "$LOGS/hub_stdout.log" 2>&1 &)
    echo "       Esperando Hub..."
    wait_for "http://localhost:8234/" "Hub"
    echo " [OK] Hub en línea en :8234"
fi

# ── [2/3] Frontend (Vite) ───────────────────────────────────────────────────
if curl -s -o /dev/null "http://localhost:5500/"; then
    echo " [OK] Frontend ya está corriendo en :5500"
else
    echo " [2/3] Arrancando frontend (Vite)..."
    (cd "$REPO/frontend" && nohup npm run dev >> "$LOGS/frontend_stdout.log" 2>&1 &)
    echo "       Esperando frontend..."
    wait_for "http://localhost:5500/" "Frontend"
    echo " [OK] Frontend en línea en :5500"
fi

# ── [3/3] Ventana nativa (pywebview) ────────────────────────────────────────
echo " [3/3] Abriendo ventana de escritorio..."
echo ""
echo "=========================================="
echo "  AgentOS listo."
echo "=========================================="
echo ""

# Bloqueante a propósito (igual que el .bat): esta es la ventana que ve el
# usuario. Hub y Vite quedan corriendo en background aunque se cierre.
"$VENV/bin/python" "$REPO/desktop_shell.py"
