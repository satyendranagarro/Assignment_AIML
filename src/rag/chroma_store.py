"""Chroma vector store build + load for Singapore KB chunks."""

from __future__ import annotations

import os
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


def chroma_server_settings() -> tuple[str, int] | None:
    """Return (host, port) when CHROMA_HOST is set (Phase 1.5 Compose); else None for local path."""
    host = (os.getenv("CHROMA_HOST") or "").strip()
    if not host:
        return None
    port = int(os.getenv("CHROMA_PORT") or "8000")
    return host, port


def _http_client(host: str, port: int) -> Any:
    import chromadb

    return chromadb.HttpClient(host=host, port=port)


def _reset_collection(client: Any, collection_name: str) -> None:
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass


def build_chroma(
    chunks: list[Chunk],
    *,
    embeddings: Embeddings,
    persist_dir: Path | str = DEFAULT_CHROMA,
    collection_name: str = COLLECTION_NAME,
    reset: bool = True,
) -> Any:
    """Embed chunks into a Chroma collection (local path or CHROMA_HOST server)."""
    from langchain_chroma import Chroma

    server = chroma_server_settings()
    if server:
        host, port = server
        client = _http_client(host, port)
        if reset:
            _reset_collection(client, collection_name)
        store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            client=client,
        )
    else:
        path = Path(persist_dir)
        if reset and path.exists():
            for child in path.iterdir():
                if child.name == ".gitkeep":
                    continue
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        path.mkdir(parents=True, exist_ok=True)
        store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=str(path),
        )

    docs = chunks_to_documents(chunks)
    if docs:
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
        mode="server" if server else "persistent",
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

    server = chroma_server_settings()
    if server:
        host, port = server
        client = _http_client(host, port)
        return Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            client=client,
        )

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
