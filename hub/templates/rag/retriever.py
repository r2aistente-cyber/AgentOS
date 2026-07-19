"""Recupera los chunks de knowledge más relevantes para una query.

Usa ChromaDB + sentence-transformers para búsqueda semántica.
Si el índice no existe o está vacío, retorna string vacío (sin romper el flujo).
"""
from __future__ import annotations

from pathlib import Path

import agent_config as config

TOP_K = 5           # fragmentos a recuperar por query
MAX_CHARS = 6000    # tope de chars totales inyectados en el prompt


def _get_index_dir() -> Path:
    base = Path(config.get("agent.install_path") or Path(__file__).resolve().parents[1])
    return base / "data" / "rag_index"


def retrieve(query: str) -> str:
    """Retorna un bloque Markdown con los chunks relevantes, listo para inyectar en el prompt."""
    index_dir = _get_index_dir()
    if not index_dir.exists():
        return ""

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer

        client = chromadb.PersistentClient(path=str(index_dir))
        collection = client.get_collection("knowledge")

        if collection.count() == 0:
            return ""

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode([query], show_progress_bar=False).tolist()[0]

        results = collection.query(
            query_embeddings=[embedding],
            n_results=min(TOP_K, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not docs:
            return ""

        parts = ["## 📚 Knowledge relevante\n"]
        total_chars = 0

        for doc, meta, dist in zip(docs, metas, distances):
            if total_chars >= MAX_CHARS:
                break
            # dist es distancia coseno [0,2]; similaridad = 1 - dist/2
            similarity = round(1 - dist / 2, 2)
            if similarity < 0.15:  # descartar chunks irrelevantes
                continue
            source = Path(meta.get("source", "")).name
            snippet = doc[:MAX_CHARS - total_chars].strip()
            parts.append(f"**[{source}]** *(relevancia: {similarity})*\n```\n{snippet}\n```\n")
            total_chars += len(snippet)

        if len(parts) == 1:  # solo el header, sin contenido útil
            return ""

        return "\n".join(parts)

    except Exception:
        return ""
