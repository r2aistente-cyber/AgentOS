"""Tests del catálogo de modelos por proveedor (hub/catalog.py)."""
from __future__ import annotations

import pytest
from hub.catalog import PROVIDER_CATALOGS, get_catalog


# ─── Estructura del catálogo ──────────────────────────────────────────────────

def test_catalog_contiene_todos_los_proveedores():
    """Todos los proveedores conocidos tienen entrada en PROVIDER_CATALOGS."""
    expected = {"opencode-go", "opencode", "openai", "anthropic", "ollama", "mock", "custom"}
    assert expected <= set(PROVIDER_CATALOGS.keys())


def test_catalog_opencode_go_tiene_modelos():
    models = PROVIDER_CATALOGS["opencode-go"]
    assert isinstance(models, list)
    assert len(models) > 0
    assert all(isinstance(m, str) and m for m in models), "Todos los modelos deben ser strings no vacíos"


def test_catalog_opencode_zen_tiene_modelos():
    models = PROVIDER_CATALOGS["opencode"]
    assert isinstance(models, list)
    assert len(models) > 0


def test_catalog_openai_tiene_modelos():
    models = PROVIDER_CATALOGS["openai"]
    assert isinstance(models, list)
    assert any("gpt" in m for m in models)


def test_catalog_anthropic_tiene_modelos():
    models = PROVIDER_CATALOGS["anthropic"]
    assert isinstance(models, list)
    assert any("claude" in m for m in models)


def test_catalog_ollama_es_none():
    """Ollama no tiene catálogo fijo — el usuario escribe el modelo."""
    assert PROVIDER_CATALOGS["ollama"] is None


def test_catalog_custom_es_none():
    assert PROVIDER_CATALOGS["custom"] is None


def test_catalog_mock_tiene_al_menos_un_modelo():
    models = PROVIDER_CATALOGS["mock"]
    assert models is not None and len(models) > 0


# ─── get_catalog ──────────────────────────────────────────────────────────────

def test_get_catalog_proveedor_valido():
    result = get_catalog("openai")
    assert result is not None
    assert isinstance(result, list)


def test_get_catalog_ollama_retorna_none():
    assert get_catalog("ollama") is None


def test_get_catalog_proveedor_inexistente_retorna_none():
    assert get_catalog("proveedor_que_no_existe_jamas") is None


def test_todos_los_modelos_son_strings_validos():
    """Todos los modelos en todos los catálogos fijos son strings no vacíos."""
    for provider, models in PROVIDER_CATALOGS.items():
        if models is None:
            continue
        for model in models:
            assert isinstance(model, str) and model.strip(), (
                f"Modelo inválido '{model}' en proveedor '{provider}'"
            )
