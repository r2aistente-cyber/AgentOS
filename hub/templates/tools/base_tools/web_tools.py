"""Tools web: búsqueda y fetch de URLs."""
from __future__ import annotations

import httpx

from tools.registry import ToolDef, register


async def search_web(query: str, max_results: int = 5) -> str:
    import asyncio
    try:
        from duckduckgo_search import DDGS

        def _sync_search():
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}")
            return results

        results = await asyncio.to_thread(_sync_search)
        return "\n\n---\n\n".join(results) if results else "Sin resultados."
    except Exception as e:  # noqa: BLE001
        return f"Error en búsqueda: {e}"


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
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines[:200])


register(ToolDef("search_web", "Busca información en internet (DuckDuckGo).", "web",
    {"type": "object", "properties": {
        "query": {"type": "string", "description": "Términos de búsqueda"},
        "max_results": {"type": "integer", "default": 5}},
     "required": ["query"]}, search_web))

register(ToolDef("fetch_url", "Obtiene y extrae el texto legible de una URL.", "web",
    {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    fetch_url))
