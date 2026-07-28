"""Resuelve specialties/*.json + skills/*.yaml a un config_body para
AgentManager.create() — sin esto, esos archivos son solo texto aspiracional
que nadie carga (ver specialties/r2-legal.json, skills/derecho-general.yaml).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from hub import config


def _load_specialty(specialty_id: str) -> dict[str, Any]:
    path = config.specialties_dir() / f"{specialty_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No existe specialties/{specialty_id}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_skill(name: str) -> dict[str, Any]:
    path = config.skills_dir() / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No existe skills/{name}.yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _merge_specialty(base: dict, child: dict) -> dict[str, Any]:
    """Combina dos specialties: listas se unen sin duplicar, dicts se
    mezclan recursivo, escalares el hijo (child) gana sobre el padre (base).

    Excepción deliberada: `tools.allow` NO se une, el hijo reemplaza al padre
    si lo declara. `core` (la base de todos los specialties) usa `["*"]"`
    (acceso total, es el asistente personal de Xavier) — unir esa lista con
    la de un specialty más restringido como r2-legal anularía la
    restricción por completo (bastaría con que "*" apareciera una vez en
    cualquier ancestro para que el hijo también quede sin restricción).
    """
    out = dict(base)
    for key, value in child.items():
        if key == "extends":
            continue
        existing = out.get(key)
        if key == "tools" and isinstance(value, dict) and isinstance(existing, dict):
            merged_tools = dict(existing)
            for tk, tv in value.items():
                merged_tools[tk] = tv if tk == "allow" else (
                    _merge_specialty(merged_tools.get(tk, {}), tv)
                    if isinstance(tv, dict) and isinstance(merged_tools.get(tk), dict)
                    else tv
                )
            out[key] = merged_tools
        elif isinstance(value, list) and isinstance(existing, list):
            out[key] = existing + [v for v in value if v not in existing]
        elif isinstance(value, dict) and isinstance(existing, dict):
            out[key] = _merge_specialty(existing, value)
        else:
            out[key] = value
    return out


def _resolve_chain(specialty_id: str, _seen: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Resuelve la cadena `extends` (padres primero), el hijo sobreescribe."""
    if specialty_id in _seen:
        raise ValueError(f"Ciclo de 'extends' detectado en specialty '{specialty_id}'")
    seen = _seen | {specialty_id}

    spec = _load_specialty(specialty_id)
    merged: dict[str, Any] = {}
    for parent_id in spec.get("extends") or []:
        merged = _merge_specialty(merged, _resolve_chain(parent_id, seen))
    return _merge_specialty(merged, spec)


def resolve_specialty(specialty_id: str) -> dict[str, Any]:
    """Devuelve {"config_body", "knowledge_source_files", "missing_knowledge_files"}.

    `config_body` tiene la misma forma que ya acepta AgentManager.create()
    (system_prompt, tools.allow, llm, personality, security.sandbox_paths,
    mcp_servers — ver tools/mcp_client.py en el template, que descubre y
    registra dinámicamente las tools de cada servidor MCP configurado, en
    vez de necesitar un archivo de tools escrito a mano por integración).
    `knowledge_source_files` son Paths absolutos (bajo raíz/knowledge/) para
    copiar al workspace del agente una vez creado — eso lo hace el caller
    (hub/api/agents.py), no este módulo.
    """
    spec = _resolve_chain(specialty_id)

    prompt_parts: list[str] = []
    base_prompt = (spec.get("personality") or {}).get("system_prompt")
    if base_prompt:
        prompt_parts.append(base_prompt.strip())

    tools_allow: list[str] = list((spec.get("tools") or {}).get("allow") or [])
    knowledge_filenames: list[str] = list(spec.get("knowledge_files") or [])

    for skill_name in spec.get("skills") or []:
        skill = _load_skill(skill_name)
        skill_prompt = skill.get("prompt")
        if skill_prompt:
            prompt_parts.append(skill_prompt.strip())
        for t in skill.get("tools") or []:
            if t not in tools_allow:
                tools_allow.append(t)
        for kf in skill.get("knowledge_files") or []:
            if kf not in knowledge_filenames:
                knowledge_filenames.append(kf)

    config_body: dict[str, Any] = {
        "system_prompt": "\n\n".join(prompt_parts),
        "tools": {"allow": tools_allow},
    }

    personality = {k: v for k, v in (spec.get("personality") or {}).items()
                   if k != "system_prompt"}
    if personality:
        config_body["personality"] = personality

    model = spec.get("model")
    if model:
        config_body["llm"] = dict(model)

    sandbox_paths = (spec.get("sandbox") or {}).get("paths")
    if sandbox_paths:
        config_body["security"] = {"sandbox_paths": sandbox_paths}

    mcp_servers = spec.get("mcp_servers")
    if mcp_servers:
        config_body["mcp_servers"] = mcp_servers

    resolved_files: list[Path] = []
    missing: list[str] = []
    for filename in knowledge_filenames:
        src = config.knowledge_dir() / filename
        if src.exists():
            resolved_files.append(src)
        else:
            missing.append(filename)

    return {
        "config_body": config_body,
        "knowledge_source_files": resolved_files,
        "missing_knowledge_files": missing,
    }
