"""Shell de escritorio interino para AgentOS (sin navegador, sin compilar Tauri).

Hospeda la UI del Hub en una ventana nativa vía WebView2 (pywebview). Es la
opción 2: se ve y se siente como app nativa —sin barra de direcciones ni
pestañas— usando el runtime WebView2 ya instalado en la máquina.

Los chats por agente se abren en ventanas propias mediante una pequeña API
Python expuesta al frontend (window.pywebview.api.open_chat).

Uso:  python desktop_shell.py   (requiere Hub en :8234 y Vite en :5500)
"""
from __future__ import annotations

import webview

HUB_UI = "http://localhost:5500"


class Api:
    """Puente JS -> Python para abrir ventanas de chat nativas."""

    def open_chat(self, name: str) -> None:
        label = f"chat_{name}"
        # Si ya existe la ventana de ese agente, enfocarla en vez de duplicar.
        for w in webview.windows:
            if getattr(w, "_agentos_label", None) == label:
                try:
                    w.restore()
                except Exception:
                    pass
                return
        win = webview.create_window(
            f"Chat · {name}",
            f"{HUB_UI}/chat?agent={name}",
            width=440,
            height=680,
            resizable=True,
        )
        win._agentos_label = label


if __name__ == "__main__":
    api = Api()
    webview.create_window(
        "R2 Hub · AgentOS",
        HUB_UI,
        width=1040,
        height=740,
        min_size=(820, 560),
        js_api=api,
    )
    webview.start()
