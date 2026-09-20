"""Data-engineering models for Phase 1 source registry and documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Citation:
    title: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url}


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    publisher: str
    license: str
    reuse_notes: str
    fetch_mode: str
    priority: int
    topics: tuple[str, ...]
    seed_urls: tuple[str, ...]
    allowlist_hosts: tuple[str, ...]
    citation: Citation
    # Destination scoping for BFS (empty = host allowlist only).
    url_path_prefixes: tuple[str, ...] = ()
    url_path_contains: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Source:
        citation_raw = raw.get("citation") or {}
        return cls(
            id=str(raw["id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            publisher=str(raw.get("publisher", "")),
            license=str(raw.get("license", "")),
            reuse_notes=str(raw.get("reuse_notes", "")).strip(),
            fetch_mode=str(raw.get("fetch_mode", "crawl")),
            priority=int(raw.get("priority", 99)),
            topics=tuple(raw.get("topics") or ()),
            seed_urls=tuple(raw.get("seed_urls") or (raw.get("url"),)),
            allowlist_hosts=tuple(raw.get("allowlist_hosts") or ()),
            citation=Citation(
                title=str(citation_raw.get("title") or raw["title"]),
                url=str(citation_raw.get("url") or raw["url"]),
            ),
            url_path_prefixes=tuple(raw.get("url_path_prefixes") or ()),
            url_path_contains=tuple(raw.get("url_path_contains") or ()),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["topics"] = list(self.topics)
        data["seed_urls"] = list(self.seed_urls)
        data["allowlist_hosts"] = list(self.allowlist_hosts)
        data["url_path_prefixes"] = list(self.url_path_prefixes)
        data["url_path_contains"] = list(self.url_path_contains)
        return data


@dataclass
class NormalizedDocument:
    """Normalized text unit ready for Phase 3/4 chunking."""

    doc_id: str
    source_id: str
    title: str
    url: str
    text: str
    topics: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def citation_metadata(self) -> dict[str, str]:
        return {"source_id": self.source_id, "title": self.title, "url": self.url}

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "text": self.text,
            "topics": list(self.topics),
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> NormalizedDocument:
        return cls(
            doc_id=str(raw["doc_id"]),
            source_id=str(raw["source_id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            text=str(raw.get("text", "")),
            topics=list(raw.get("topics") or []),
            extra=dict(raw.get("extra") or {}),
        )
