"""Build Chroma KB from processed docs + ontology entity metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.llm.factory import get_embeddings
from src.observability import log_event
from src.ontology.extract import load_processed_documents
from src.ontology.gate import load_entities_file
from src.ontology.models import Entity
from src.rag.chunk import Chunk, chunk_documents
from src.rag.chroma_store import DEFAULT_CHROMA, build_chroma, chroma_count

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED = REPO_ROOT / "data" / "processed"
DEFAULT_ENTITIES = REPO_ROOT / "ontology" / "entities.json"


def doc_entity_map(entities: list[Entity]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for ent in entities:
        for ev in ent.evidence:
            mapping.setdefault(ev.doc_id, []).append(ent.id)
    for doc_id, ids in mapping.items():
        mapping[doc_id] = sorted(set(ids))
    return mapping


def build_kb(
    *,
    processed_dir: Path | str = DEFAULT_PROCESSED,
    entities_path: Path | str = DEFAULT_ENTITIES,
    chroma_dir: Path | str = DEFAULT_CHROMA,
    embedding_provider: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    reset: bool = True,
) -> dict[str, Any]:
    docs = load_processed_documents(processed_dir)
    if not docs:
        raise FileNotFoundError(
            f"No processed docs under {processed_dir}. Run crawl + normalize first."
        )
    entities: list[Entity] = []
    ent_path = Path(entities_path)
    if ent_path.is_file():
        entities = load_entities_file(ent_path)

    chunks = chunk_documents(
        docs,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        doc_entity_map=doc_entity_map(entities),
    )
    embeddings = get_embeddings(embedding_provider)
    store = build_chroma(chunks, embeddings=embeddings, persist_dir=chroma_dir, reset=reset)
    count = chroma_count(store)
    summary = {
        "doc_count": len(docs),
        "chunk_count": len(chunks),
        "chroma_count": count,
        "entity_count": len(entities),
        "chroma_dir": str(chroma_dir),
        "embedding_provider": embedding_provider or "resolved",
        "sources": sorted({d.source_id for d in docs}),
    }
    log_event(
        "retrieve.index",
        "KB build complete",
        chunk_count=len(chunks),
        entity_count=len(entities),
        status="ok",
    )
    return summary


def ensure_chunks_have_citations(chunks: list[Chunk]) -> list[str]:
    errors: list[str] = []
    for c in chunks:
        if not c.title or not c.url:
            errors.append(f"{c.chunk_id}: missing title/url citation")
        if not c.source_id or not c.doc_id:
            errors.append(f"{c.chunk_id}: missing source_id/doc_id")
    return errors
