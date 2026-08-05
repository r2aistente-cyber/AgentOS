#!/usr/bin/env bash
# R2 Hub / AgentOS — Instalador macOS/Linux
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO/backend/.venv"
AGENTOS_HOME="$HOME/AgentOS"

echo ""
echo "============================================================"
echo "  R2 Hub / AgentOS — Instalador"
echo "============================================================"
echo ""

# ── Python 3.11+ ──────────────────────────────────────────────────────────────
echo "[1/6] Verificando Python..."
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo " ERROR: Python no encontrado. Instala Python 3.11+ primero."
    exit 1
fi
PYVER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYMAJ=$(echo "$PYVER" | cut -d. -f1)
PYMIN=$(echo "$PYVER" | cut -d. -f2)
if [ "$PYMAJ" -lt 3 ] || { [ "$PYMAJ" -eq 3 ] && [ "$PYMIN" -lt 11 ]; }; then
    echo " ERROR: Se requiere Python 3.11+. Tienes Python $PYVER"
    exit 1
fi
echo " [OK] Python $PYVER"

# ── Node.js ───────────────────────────────────────────────────────────────────
echo "[2/6] Verificando Node.js..."
if command -v node &>/dev/null; then
    echo " [OK] Node.js $(node --version)"
else
    echo " AVISO: Node.js no encontrado. WhatsApp sidecar no estara disponible."
    echo "        Instala Node.js 18+ desde https://nodejs.org"
fi

# ── Virtualenv ────────────────────────────────────────────────────────────────
echo "[3/6] Configurando entorno Python..."
if [ -f "$VENV/bin/python" ]; then
    echo " [OK] Virtualenv ya existe"
else
    "$PYTHON" -m venv "$VENV"
    echo " [OK] Virtualenv creado en $VENV"
fi

"$VENV/bin/pip" install -r "$REPO/hub/requirements.txt" --quiet --upgrade
"$VENV/bin/pip" install -r "$REPO/requirements-desktop.txt" --quiet --upgrade
echo " [OK] Dependencias instaladas"

# ── Estructura de directorios ─────────────────────────────────────────────────
echo "[4/6] Creando estructura AgentOS en $AGENTOS_HOME..."
mkdir -p "$AGENTOS_HOME/agents" "$AGENTOS_HOME/archived" "$AGENTOS_HOME/logs"
echo " [OK] Estructura creada"

# ── R2 PRIME ──────────────────────────────────────────────────────────────────
echo "[5/6] Creando agente R2-PRIME..."
if "$VENV/bin/python" "$REPO/setup/create_r2_prime.py"; then
    echo " [OK] R2-PRIME listo en $AGENTOS_HOME/agents/R2-PRIME"
else
    echo " AVISO: No se pudo crear R2-PRIME. Crealo desde el Hub."
fi

# ── Acceso directo (macOS) ────────────────────────────────────────────────────
echo "[6/6] Creando launcher..."
cat > "$HOME/Desktop/R2 Hub.command" 2>/dev/null << EOF
#!/bin/bash
cd "$REPO"
bash Iniciar-R2Hub.sh
EOF
chmod +x "$HOME/Desktop/R2 Hub.command" 2>/dev/null || true
echo " [OK] Launcher creado (o usa: bash $REPO/Iniciar-R2Hub.sh)"

echo ""
echo "============================================================"
echo "  Instalacion completada!"
echo "============================================================"
echo ""
echo "  Para iniciar: bash $REPO/Iniciar-R2Hub.sh"
echo "  Agentes en:   $AGENTOS_HOME/agents/"
echo ""

read -rp "  Iniciar R2 Hub ahora? [S/n]: " START
if [[ "${START,,}" != "n" ]]; then
    bash "$REPO/Iniciar-R2Hub.sh" &
fi
