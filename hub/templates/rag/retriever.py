"""Recupera los chunks de knowledge más relevantes para una query."""
from __future__ import annotations

from pathlib import Path

import agent_config as config

TOP_K = 5
MAX_CHARS = 6000

# Cache del modelo — mismo patrón que indexer.py para no recargar 90MB en cada mensaje
_model = None
_client = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_collection(index_dir: Path):
    global _client, _collection
    if _collection is None:
        import chromadb
        _client = chromadb.PersistentClient(path=str(index_dir))
        _collection = _client.get_collection("knowledge")
    return _collection


def _get_index_dir() -> Path:
    base = Path(config.get("agent.install_path") or Path(__file__).resolve().parents[1])
    return base / "data" / "rag_index"


def retrieve(query: str) -> str:
    index_dir = _get_index_dir()
    if not index_dir.exists():
        return ""

    try:
        collection = _get_collection(index_dir)

        if collection.count() == 0:
            return ""

        model = _get_model()
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

        parts = ["## Knowledge relevante\n"]
        total_chars = 0

        for doc, meta, dist in zip(docs, metas, distances):
            if total_chars >= MAX_CHARS:
                break
            similarity = round(1 - dist / 2, 2)
            if similarity < 0.15:
                continue
            source = Path(meta.get("source", "")).name
            snippet = doc[:MAX_CHARS - total_chars].strip()
            parts.append(f"**[{source}]** (relevancia: {similarity})\n```\n{snippet}\n```\n")
            total_chars += len(snippet)

        if len(parts) == 1:
            return ""

        return "\n".join(parts)

    except Exception:
        return ""
