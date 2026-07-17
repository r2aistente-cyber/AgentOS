"""Herramientas web: búsqueda y fetch de URLs."""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from backend.tools.registry import ToolDef, register


async def search_web(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(f"**{r['title']}**\n{r['href']}\n{r['body']}")
        return "\n\n---\n\n".join(results) if results else "Sin resultados."
    except Exception as e:
        return f"Error en búsqueda: {e}"


async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "R2-Autonomous/1.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines[:200])


# ─── Registro ─────────────────────────────────────────────────────────────

register(ToolDef(
    name="search_web",
    description="Busca información en internet usando DuckDuckGo.",
    category="web",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Términos de búsqueda"},
            "max_results": {"type": "integer", "description": "Número de resultados (default 5)", "default": 5},
        },
        "required": ["query"],
    },
    handler=search_web,
))

register(ToolDef(
    name="fetch_url",
    description="Obtiene y extrae el texto legible de una URL.",
    category="web",
    min_level=1,
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "URL a obtener"}},
        "required": ["url"],
    },
    handler=fetch_url,
))
