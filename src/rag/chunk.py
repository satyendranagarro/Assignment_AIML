"""Chunk models and citation-preserving text splitting."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from src.data.models import NormalizedDocument

_WS_RE = re.compile(r"\s+")


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_id: str
    title: str
    url: str
    text: str
    topics: list[str] = field(default_factory=list)
    entity_ids: list[str] = field(default_factory=list)
    chunk_index: int = 0

    def metadata(self) -> dict[str, Any]:
        # Chroma metadata values must be str/int/float/bool
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "topics": ",".join(self.topics),
            "entity_ids": ",".join(self.entity_ids),
            "chunk_index": self.chunk_index,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Chunk:
        return cls(
            chunk_id=str(raw["chunk_id"]),
            doc_id=str(raw["doc_id"]),
            source_id=str(raw["source_id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            text=str(raw["text"]),
            topics=list(raw.get("topics") or []),
            entity_ids=list(raw.get("entity_ids") or []),
            chunk_index=int(raw.get("chunk_index", 0)),
        )


def _make_chunk_id(doc_id: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{doc_id}|{index}|{text[:64]}".encode()).hexdigest()[:10]
    return f"{doc_id}__c{index:03d}__{digest}"


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[str]:
    """Split text into overlapping windows preferring paragraph boundaries."""
    if chunk_size < 100:
        raise ValueError("chunk_size must be >= 100")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be < chunk_size")

    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        cleaned = _WS_RE.sub(" ", buf).strip()
        if cleaned:
            chunks.append(cleaned)
        buf = ""

    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= chunk_size:
            buf = candidate
            continue
        if buf:
            flush()
        if len(para) <= chunk_size:
            buf = para
            continue
        # Hard-split long paragraph
        start = 0
        while start < len(para):
            end = min(len(para), start + chunk_size)
            piece = para[start:end].strip()
            if piece:
                chunks.append(_WS_RE.sub(" ", piece))
            if end >= len(para):
                break
            start = max(end - chunk_overlap, start + 1)

    flush()
    return chunks


def chunk_document(
    doc: NormalizedDocument,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    entity_ids: Iterable[str] | None = None,
) -> list[Chunk]:
    texts = chunk_text(doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    ents = list(entity_ids or [])
    out: list[Chunk] = []
    for i, text in enumerate(texts):
        out.append(
            Chunk(
                chunk_id=_make_chunk_id(doc.doc_id, i, text),
                doc_id=doc.doc_id,
                source_id=doc.source_id,
                title=doc.title,
                url=doc.url,
                text=text,
                topics=list(doc.topics),
                entity_ids=ents,
                chunk_index=i,
            )
        )
    return out


def chunk_documents(
    docs: list[NormalizedDocument],
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    doc_entity_map: dict[str, list[str]] | None = None,
) -> list[Chunk]:
    mapping = doc_entity_map or {}
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(
            chunk_document(
                doc,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                entity_ids=mapping.get(doc.doc_id, []),
            )
        )
    return chunks
