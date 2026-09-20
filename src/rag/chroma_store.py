"""Chroma vector store build + load for Singapore KB chunks."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.observability import log_event
from src.rag.chunk import Chunk

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA = REPO_ROOT / "data" / "chroma"
COLLECTION_NAME = "singapore_kb"


def chunks_to_documents(chunks: list[Chunk]) -> list[Document]:
    return [
        Document(page_content=c.text, metadata=c.metadata(), id=c.chunk_id)
        for c in chunks
    ]


def build_chroma(
    chunks: list[Chunk],
    *,
    embeddings: Embeddings,
    persist_dir: Path | str = DEFAULT_CHROMA,
    collection_name: str = COLLECTION_NAME,
    reset: bool = True,
) -> Any:
    """Embed chunks into a persistent Chroma collection."""
    from langchain_chroma import Chroma

    path = Path(persist_dir)
    if reset and path.exists():
        # Keep .gitkeep if present
        for child in path.iterdir():
            if child.name == ".gitkeep":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    path.mkdir(parents=True, exist_ok=True)

    docs = chunks_to_documents(chunks)
    store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(path),
    )
    if docs:
        # Prefer ids when supported
        ids = [c.chunk_id for c in chunks]
        try:
            store.add_documents(docs, ids=ids)
        except TypeError:
            store.add_documents(docs)

    log_event(
        "retrieve.index",
        "Built Chroma collection",
        store="chroma",
        chunk_count=len(chunks),
        status="ok",
    )
    return store


def load_chroma(
    *,
    embeddings: Embeddings,
    persist_dir: Path | str = DEFAULT_CHROMA,
    collection_name: str = COLLECTION_NAME,
) -> Any:
    from langchain_chroma import Chroma

    path = Path(persist_dir)
    if not path.is_dir():
        raise FileNotFoundError(f"Chroma path not found: {path}")
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(path),
    )


def chroma_count(store: Any) -> int:
    try:
        return int(store._collection.count())  # noqa: SLF001
    except Exception:
        try:
            return len(store.get()["ids"])
        except Exception:
            return 0
