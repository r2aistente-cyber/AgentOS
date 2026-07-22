"""Tools web: búsqueda y fetch de URLs.

Búsqueda: usa Brave Search si hay API key configurada (search.brave_api_key),
cae a DuckDuckGo gratis si no hay key (requiere pip install duckduckgo-search).
"""
from __future__ import annotations

import asyncio

import httpx

import agent_config as config
from tools.registry import ToolDef, register

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


async def _brave_search(query: str, api_key: str, max_results: int) -> list[str]:
    params = {"q": query, "count": min(max_results, 20), "text_decorations": False}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            _BRAVE_URL,
            params=params,
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
        )
        r.raise_for_status()
        data = r.json()
    items = data.get("web", {}).get("results", [])
    return [f"**{it['title']}**\n{it['url']}\n{it.get('description', '')}" for it in items]


async def _ddg_search(query: str, max_results: int) -> list[str]:
    def _sync():
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}")
        return results
    return await asyncio.to_thread(_sync)


async def search_web(query: str, max_results: int = 5) -> str:
    brave_key = (config.get("search", {}) or {}).get("brave_api_key") or ""
    try:
        if brave_key:
            results = await _brave_search(query, brave_key, max_results)
        else:
            results = await _ddg_search(query, max_results)
        return "\n\n---\n\n".join(results) if results else "Sin resultados."
    except Exception as e:  # noqa: BLE001
        provider = "Brave" if brave_key else "DuckDuckGo"
        return f"Error en búsqueda ({provider}): {e}"


async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "R2-Agent/1.0"})
        r.raise_for_status()
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        except Exception:  # noqa: BLE001
            text = r.text
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines[:200])


register(ToolDef("search_web", "Busca información en internet (Brave o DuckDuckGo).", "web",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "Términos de búsqueda"},
        "max_results": {"type": "integer", "default": 5}},
     "required": ["query"]}, search_web))

register(ToolDef("fetch_url", "Obtiene y extrae el texto legible de una URL.", "web",
    {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    fetch_url))
