"""Tests de web tools (hub/templates/tools/base_tools/web_tools.py).

- fetch_url: mock de httpx.AsyncClient
- search_web: mock de duckduckgo_search.DDGS
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── fetch_url ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_url_retorna_texto(template_env):
    from tools.base_tools.web_tools import fetch_url

    mock_response = MagicMock()
    mock_response.text = "<html><body><p>Hola mundo</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_url("https://example.com")

    assert "Hola mundo" in result


@pytest.mark.asyncio
async def test_fetch_url_sin_beautifulsoup_usa_texto_crudo(template_env):
    """Si BeautifulSoup no está disponible, se usa r.text directamente."""
    from tools.base_tools.web_tools import fetch_url

    mock_response = MagicMock()
    mock_response.text = "contenido crudo\nlínea dos"
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("builtins.__import__", side_effect=lambda n, *a, **k: (_ for _ in ()).throw(ImportError) if n == "bs4" else __import__(n, *a, **k)):
        result = await fetch_url("https://example.com")

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_fetch_url_limita_200_lineas(template_env):
    from tools.base_tools.web_tools import fetch_url

    # Generar 300 líneas de texto
    lineas = [f"línea {i}" for i in range(300)]
    mock_response = MagicMock()
    mock_response.text = "\n".join(lineas)
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_url("https://example.com")

    assert len(result.splitlines()) <= 200


@pytest.mark.asyncio
async def test_fetch_url_http_error_propaga(template_env):
    import httpx
    from tools.base_tools.web_tools import fetch_url

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    ))

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(Exception):
        await fetch_url("https://example.com/no-existe")


# ─── search_web ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_web_retorna_resultados(template_env):
    from tools.base_tools.web_tools import search_web

    fake_results = [
        {"title": "Resultado 1", "href": "https://r1.com", "body": "Descripción 1"},
        {"title": "Resultado 2", "href": "https://r2.com", "body": "Descripción 2"},
    ]

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(return_value=fake_results)

    mock_ddgs_class = MagicMock(return_value=mock_ddgs)

    with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
        import importlib
        import tools.base_tools.web_tools as wt
        importlib.reload(wt)
        result = await wt.search_web("python asyncio", max_results=2)

    assert "Resultado 1" in result
    assert "Resultado 2" in result


@pytest.mark.asyncio
async def test_search_web_sin_resultados(template_env):
    from tools.base_tools.web_tools import search_web

    mock_ddgs = MagicMock()
    mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_ddgs.__exit__ = MagicMock(return_value=False)
    mock_ddgs.text = MagicMock(return_value=[])

    mock_ddgs_class = MagicMock(return_value=mock_ddgs)

    with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
        import importlib
        import tools.base_tools.web_tools as wt
        importlib.reload(wt)
        result = await wt.search_web("xyzw nada encontrado")

    assert "Sin resultados" in result


@pytest.mark.asyncio
async def test_search_web_sin_duckduckgo_retorna_error(template_env):
    """Si duckduckgo_search no está instalado, retorna mensaje de error."""
    from tools.base_tools.web_tools import search_web

    with patch.dict("sys.modules", {"duckduckgo_search": None}):
        import importlib
        import tools.base_tools.web_tools as wt
        importlib.reload(wt)
        result = await wt.search_web("test")

    assert "Error" in result


@pytest.mark.asyncio
async def test_search_web_excepcion_de_red_retorna_error(template_env):
    from tools.base_tools.web_tools import search_web

    mock_ddgs_class = MagicMock(side_effect=ConnectionError("sin red"))

    with patch.dict("sys.modules", {"duckduckgo_search": MagicMock(DDGS=mock_ddgs_class)}):
        import importlib
        import tools.base_tools.web_tools as wt
        importlib.reload(wt)
        result = await wt.search_web("test")

    assert "Error" in result


# ─── Registro en el registry ─────────────────────────────────────────────────

def test_web_tools_registradas(template_env):
    import tools.base_tools.web_tools  # noqa: F401
    from tools import registry
    names = {t.name for t in registry.all_tools()}
    assert "fetch_url" in names
    assert "search_web" in names
