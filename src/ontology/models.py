"""Ontology entity models for Phase 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    source_id: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Relation:
    type: str
    target: str

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "target": self.target}


@dataclass
class Entity:
    id: str
    name: str
    class_: str
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    spot_checked: bool = False
    spot_check_notes: str = ""

    @property
    def class_name(self) -> str:
        return self.class_

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "class": self.class_,
            "aliases": list(self.aliases),
            "tags": list(self.tags),
            "relations": [r.to_dict() for r in self.relations],
            "evidence": [e.to_dict() for e in self.evidence],
            "spot_checked": self.spot_checked,
            "spot_check_notes": self.spot_check_notes,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Entity:
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            class_=str(raw.get("class") or raw.get("class_")),
            aliases=list(raw.get("aliases") or []),
            tags=list(raw.get("tags") or []),
            relations=[
                Relation(type=str(r["type"]), target=str(r["target"]))
                for r in (raw.get("relations") or [])
            ],
            evidence=[
                Evidence(
                    doc_id=str(e["doc_id"]),
                    source_id=str(e["source_id"]),
                    url=str(e["url"]),
                    snippet=str(e["snippet"]),
                )
                for e in (raw.get("evidence") or [])
            ],
            spot_checked=bool(raw.get("spot_checked", False)),
            spot_check_notes=str(raw.get("spot_check_notes", "")),
        )
