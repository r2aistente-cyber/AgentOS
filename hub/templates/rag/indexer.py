"""Indexa los archivos de knowledge del agente en ChromaDB.

Flujo:
  1. Lee las rutas de `config.knowledge`.
  2. Chunkea cada archivo en fragmentos de ~400 tokens con 50 de overlap.
  3. Embede con sentence-transformers (all-MiniLM-L6-v2, ~90MB one-time download).
  4. Almacena en ChromaDB persistente en data/rag_index/.
  5. Solo re-indexa archivos cuyos checksums cambiaron (evita trabajo innecesario).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Generator

import agent_config as config

_SUPPORTED = {".md", ".txt", ".yaml", ".json", ".py", ".html"}
_CHUNK_SIZE = 400   # tokens aproximados (chars / 4)
_OVERLAP    = 50

# `all-MiniLM-L6-v2` es un modelo entrenado en inglés — para contenido en
# español (ej. normativa colombiana de r2-legal) sus embeddings casi no
# discriminan por tema: verificado a mano, cualquier chunk de un documento
# en español sale con similitud ~0.8+ sin importar de qué trate, lo que
# hace la búsqueda semántica poco confiable. `paraphrase-multilingual-
# MiniLM-L12-v2` sí entiende español razonablemente bien. Configurable por
# agente vía `rag.embedding_model` — DEBE ser el mismo valor acá y en
# retriever.py (comparten el mismo espacio de embeddings en la colección).
_EMBEDDING_MODEL = config.get("rag.embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")

_INDEX_DIR = Path(__file__).resolve().parent.parent / "data" / "rag_index"
_META_FILE = _INDEX_DIR / "checksums.json"

# Lazy imports — no fallan si no están instaladas hasta que se usan
_collection = None
_model = None


def _get_index_dir() -> Path:
    base = Path(config.get("agent.install_path") or Path(__file__).resolve().parents[1])
    d = base / "data" / "rag_index"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_checksums(meta: Path) -> dict[str, str]:
    if meta.exists():
        try:
            return json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _checksum(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _chunk(text: str, size: int = _CHUNK_SIZE, overlap: int = _OVERLAP) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
    return chunks


def _collect_files(paths: list[str]) -> Generator[Path, None, None]:
    for entry in paths:
        p = Path(entry).expanduser().resolve()
        if not p.exists():
            continue
        if p.is_file() and p.suffix in _SUPPORTED:
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.suffix in _SUPPORTED:
                    yield f


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(_EMBEDDING_MODEL)
    return _model


def _get_collection(index_dir: Path):
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(index_dir))
        _collection = client.get_or_create_collection(
            "knowledge",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def index(force: bool = False) -> int:
    """Indexa archivos de knowledge. Retorna número de chunks añadidos/actualizados."""
    paths = config.get("knowledge", []) or []
    if not paths:
        return 0

    index_dir = _get_index_dir()
    meta_file = index_dir / "checksums.json"
    checksums = _load_checksums(meta_file)

    files_to_index: list[Path] = []
    new_checksums = dict(checksums)

    for f in _collect_files(paths):
        cs = _checksum(f)
        key = str(f)
        if force or checksums.get(key) != cs:
            files_to_index.append(f)
            new_checksums[key] = cs

    if not files_to_index:
        return 0

    collection = _get_collection(index_dir)
    model = _get_model()
    added = 0

    for f in files_to_index:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        chunks = _chunk(text)
        if not chunks:
            continue

        # Borrar chunks viejos del mismo archivo antes de re-insertar
        try:
            existing = collection.get(where={"source": str(f)})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

        embeddings = model.encode(chunks, show_progress_bar=False).tolist()
        ids = [f"{f}::{i}" for i in range(len(chunks))]
        metadatas = [{"source": str(f), "chunk": i} for i in range(len(chunks))]

        collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        added += len(chunks)

    meta_file.write_text(json.dumps(new_checksums, indent=2), encoding="utf-8")
    return added


def has_knowledge() -> bool:
    paths = config.get("knowledge", []) or []
    return bool(paths)
