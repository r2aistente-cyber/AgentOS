"""Tests de hub/exporter.py — auditoría de huecos reales (2026-07-27):
memory.db no debe viajar (historial real de conversaciones), sandbox_paths
heredados de un specialty no deben viajar (rutas personales del dueño
original), y requirements.txt debe reflejar las dependencias reales del
agente (antes había una lista aparte, desincronizada de hub/requirements.txt,
a la que le faltaban aiosqlite/pypdf/python-docx/openpyxl/etc.)."""
from __future__ import annotations

import io
import tarfile

import pytest
import yaml

from hub import exporter


def _make_agent_dir(tmp_path):
    agent_dir = tmp_path / "agente-test"
    agent_dir.mkdir()

    config = {
        "agent": {"name": "agente-test", "port": 9000, "install_path": str(agent_dir)},
        "llm": {"provider": "opencode-go", "model": "deepseek-v4-pro",
                "api_key": "sk-secreto-real"},
        "security": {
            "level": 2,
            "token": "token-secreto-real",
            "sandbox_paths": ["~/Trantor/", "~/Documents/", "/tmp/r2-autonomous/"],
        },
        "search": {"brave_api_key": "brave-key-secreta"},
        "suite_legal": {"base_url": "http://localhost:8000/api/v1", "api_key": "otra-secreta"},
        "knowledge": [str(agent_dir / "data" / "knowledge")],
    }
    (agent_dir / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (agent_dir / "engine.py").write_text("VERSION = 1\n", encoding="utf-8")
    (agent_dir / "memory.db").write_bytes(b"contenido binario de sqlite real")
    (agent_dir / "logs").mkdir()
    (agent_dir / "logs" / "agent.log").write_text("log viejo\n", encoding="utf-8")
    data_dir = agent_dir / "data" / "knowledge"
    data_dir.mkdir(parents=True)
    (data_dir / "principios.yaml").write_text("contenido: real", encoding="utf-8")

    return agent_dir


def _extract_member(tar_bytes: bytes, name: str) -> bytes | None:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        try:
            member = tar.getmember(name)
        except KeyError:
            return None
        f = tar.extractfile(member)
        return f.read() if f else None


def _list_members(tar_bytes: bytes) -> list[str]:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tar:
        return tar.getnames()


def test_memory_db_no_se_incluye_en_el_export(tmp_path):
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    members = _list_members(pkg)
    assert "agent/memory.db" not in members
    assert not any(m.endswith("memory.db") for m in members)


def test_logs_tampoco_se_incluyen(tmp_path):
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    members = _list_members(pkg)
    assert not any("agent/logs/" in m for m in members)


def test_conocimiento_si_se_incluye(tmp_path):
    """El conocimiento (RAG) sí debe viajar — solo memory.db/logs/secretos se excluyen."""
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    content = _extract_member(pkg, "agent/data/knowledge/principios.yaml")
    assert content is not None
    assert b"contenido: real" in content


def test_sandbox_paths_heredados_no_viajan(tmp_path):
    """Rutas personales del dueño original (~/Trantor/, etc., heredadas de
    un specialty como 'core') no deben aparecer en el config exportado."""
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    raw_cfg = _extract_member(pkg, "agent/config.yaml")
    cfg = yaml.safe_load(raw_cfg)

    assert "sandbox_paths" not in cfg.get("security", {})
    # el resto de security.* que no es sensible se conserva
    assert cfg["security"]["level"] == 2


def test_secretos_existentes_siguen_sin_viajar(tmp_path):
    """No regresión: el comportamiento de stripping de secretos ya existente
    (api_key, token, brave_api_key) se preserva tras agregar sandbox_paths."""
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    raw_cfg = _extract_member(pkg, "agent/config.yaml")
    cfg = yaml.safe_load(raw_cfg)

    assert "api_key" not in cfg.get("llm", {})
    assert "token" not in cfg.get("security", {})
    assert "brave_api_key" not in cfg.get("search", {})
    assert "api_key" not in cfg.get("suite_legal", {})


def test_requirements_incluye_dependencias_reales_no_solo_la_lista_vieja(tmp_path):
    """La lista hardcodeada vieja no incluía aiosqlite (memory/db.py la usa
    directamente) ni pypdf/python-docx/openpyxl/python-multipart/pydantic —
    un agente exportado con esa lista fallaba al arrancar. Ahora se lee de
    hub/requirements.txt (o el fallback, si no existiera)."""
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    raw_reqs = _extract_member(pkg, "requirements.txt")
    assert raw_reqs is not None
    reqs = raw_reqs.decode("utf-8")

    for paquete_critico in ("fastapi", "uvicorn", "httpx", "aiosqlite", "python-multipart"):
        assert paquete_critico in reqs, f"falta {paquete_critico} en requirements.txt exportado"


def test_telegram_bot_token_no_viaja_en_el_export(tmp_path):
    """channels.telegram.bot_token es tan secreto como llm.api_key — quien
    reciba el paquete no debe heredar el bot de Telegram del dueño original."""
    agent_dir = _make_agent_dir(tmp_path)
    cfg = yaml.safe_load((agent_dir / "config.yaml").read_text(encoding="utf-8"))
    cfg["channels"] = {"telegram": {"enabled": True, "bot_token": "123456:AAtoken-secreto",
                                     "allowed_users": ["987654321"]}}
    (agent_dir / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")

    pkg = exporter.export_agent("agente-test", agent_dir)
    raw_cfg = _extract_member(pkg, "agent/config.yaml")
    out = yaml.safe_load(raw_cfg)

    assert "bot_token" not in out["channels"]["telegram"]
    # allowed_users es específico del dueño original (sus chat_id de
    # Telegram) — tampoco debe viajar, quien importe configura el suyo.
    assert "allowed_users" not in out["channels"]["telegram"]
    # enabled sí es config legítima del agente, no un secreto — se conserva.
    assert out["channels"]["telegram"]["enabled"] is True


def test_requirements_lee_el_archivo_real_del_repo(tmp_path):
    """Confirma que se lee hub/requirements.txt de verdad (no el fallback) —
    si alguien agrega una dependencia nueva ahí (ej. `mcp` para la
    integración por MCP), el export la refleja sin tocar exporter.py."""
    agent_dir = _make_agent_dir(tmp_path)
    pkg = exporter.export_agent("agente-test", agent_dir)

    raw_reqs = _extract_member(pkg, "requirements.txt").decode("utf-8")
    real_file = exporter._REQUIREMENTS_PATH.read_text(encoding="utf-8")

    assert raw_reqs == real_file
