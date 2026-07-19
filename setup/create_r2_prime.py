"""Crea el agente R2-PRIME en AgentOS sin necesitar el Hub corriendo.

Usado por install.bat / install.sh durante la instalación inicial.
Si R2-PRIME ya existe, no hace nada.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Añadir el repo al PYTHONPATH
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from hub.agent_manager import AgentManager  # noqa: E402

R2_PRIME_CONFIG = {
    "agent": {
        "description": "Asistente personal — arquitecto de software, directo, ligeramente sarcástico",
    },
    "personality": {
        "system_prompt": (
            "Eres R2 PRIME, el asistente personal y arquitecto de software de confianza.\n\n"
            "Personalidad:\n"
            "- Directo y conciso. Sin relleno corporativo.\n"
            "- Ligeramente sarcástico cuando algo es ineficiente, pero siempre resuelves primero.\n"
            "- Tienes opiniones y las expresas.\n"
            "- El sarcasmo es la salsa, no el plato principal.\n\n"
            "Reglas:\n"
            "- Responde en español a menos que el usuario escriba en otro idioma.\n"
            "- Usa tus tools para obtener información del sistema en vez de pedirle al usuario.\n"
            "- Antes de ejecutar comandos destructivos, confirma primero.\n"
            "- Prioridad: ser útil > ser gracioso."
        ),
        "tone": "directo",
        "humor": "sarcastico",
    },
    "llm": {
        "provider": "ollama",
        "model": "qwen2.5:latest",
        "temperature": 0.7,
        "num_ctx": 16384,
        "models": [
            {"provider": "ollama", "model": "qwen2.5:latest", "label": "Qwen 2.5 (general)"},
            {"provider": "ollama", "model": "qwen2.5-coder:3b", "label": "Qwen Coder 3B (rápido)"},
        ],
    },
    "tools": {
        "allow": [
            "read_file", "write_file", "list_files", "search_files",
            "search_web", "fetch_url",
            "save_memory", "get_memory", "list_memories",
            "exec_command",
            "git_status", "git_log", "git_diff", "git_show",
        ]
    },
    "security": {"level": 2},
    "auto_restart": True,
}


def main() -> int:
    manager = AgentManager()
    if "R2-PRIME" in manager.agents:
        print("R2-PRIME ya existe — omitiendo creación")
        return 0
    try:
        info = manager.create("R2-PRIME", R2_PRIME_CONFIG)
        print(f"R2-PRIME creado en {info.dir} (puerto {info.port})")
        return 0
    except Exception as e:
        print(f"Error al crear R2-PRIME: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
