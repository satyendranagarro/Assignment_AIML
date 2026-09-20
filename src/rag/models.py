"""Retrieval hit models shared by Chroma + graph expanders."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RetrievalHit:
    text: str
    score: float
    source: str  # "chroma" | "neo4j"
    title: str = ""
    url: str = ""
    doc_id: str = ""
    source_id: str = ""
    chunk_id: str = ""
    entity_id: str = ""
    entity_class: str = ""
    relation_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def citation(self) -> dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "source_id": self.source_id,
            "doc_id": self.doc_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
