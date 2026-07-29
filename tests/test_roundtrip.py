"""Test end-to-end de export -> import -> arranca -> responde.

Ningún test anterior probaba la cadena completa: test_exporter.py y
test_importer.py testean cada módulo aislado (¿el paquete tiene los
archivos correctos? ¿el config se reescribe bien?), pero nunca que el
resultado de una importación real efectivamente arranca como proceso y
sirve tráfico -- que es la única prueba que de verdad importa antes de
confiar en export/import como vía para migrar la instalación de un
despacho real a otra máquina (ver plan Stream A).

Usa un agent_main.py mínimo (no el engine completo con RAG/tools/LLM) a
propósito: lo que este test valida es la tubería de AgentOS (export
empaqueta bien, import reescribe bien, el proceso resultante arranca con
el puerto correcto y responde en su health endpoint) -- no el
comportamiento del engine en sí, que ya tiene su propia cobertura.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import yaml

from hub import exporter, importer

_FAKE_AGENT_MAIN = """
from fastapi import FastAPI

app = FastAPI()


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
"""


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_real_agent_dir(tmp_path) -> Path:
    agent_dir = tmp_path / "origen" / "agente-roundtrip"
    agent_dir.mkdir(parents=True)
    config = {
        "agent": {"name": "agente-roundtrip", "port": 9999, "install_path": str(agent_dir)},
        "security": {"level": 2, "token": "token-original-no-deberia-viajar"},
    }
    (agent_dir / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (agent_dir / "agent_main.py").write_text(_FAKE_AGENT_MAIN, encoding="utf-8")
    return agent_dir


@pytest.mark.slow
def test_export_import_arranca_y_responde(tmp_path):
    origen = _make_real_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-roundtrip", origen)

    dest_base = tmp_path / "destino"
    dest_base.mkdir()
    puerto = _puerto_libre()
    name, agent_dir, cfg = importer.import_agent(
        pkg, dest_base, assign_port=puerto, existing_names=set()
    )

    assert name == "agente-roundtrip"
    assert cfg["agent"]["port"] == puerto
    # El token original nunca viaja (exporter lo elimina); el importado
    # siempre genera uno nuevo -- confirma que este roundtrip real se
    # comporta igual que lo que ya prueba test_importer.py de forma aislada.
    assert cfg["security"]["token"] != "token-original-no-deberia-viajar"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "agent_main:app",
         "--host", "127.0.0.1", f"--port={puerto}"],
        cwd=str(agent_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        url = f"http://127.0.0.1:{puerto}/api/v1/health"
        deadline = time.monotonic() + 15
        ultimo_error: Exception | None = None
        resp = None
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(url, timeout=1)
                if resp.status_code == 200:
                    break
            except httpx.HTTPError as e:
                ultimo_error = e
            time.sleep(0.3)

        if resp is None or resp.status_code != 200:
            salida = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            pytest.fail(
                f"El agente importado no respondió en {url} a tiempo "
                f"(último error: {ultimo_error}).\nSalida del proceso:\n{salida}"
            )

        assert resp.json() == {"status": "ok"}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
