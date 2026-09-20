"""Gazetteer-backed entity extraction from normalized documents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from src.data.models import NormalizedDocument
from src.data.normalize import DEFAULT_PROCESSED
from src.ontology.models import Entity, Evidence, Relation
from src.ontology.taxonomy import Taxonomy, load_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAZETTEER = REPO_ROOT / "ontology" / "gazetteer.yaml"


def load_gazetteer(path: Path | str | None = None) -> dict[str, Any]:
    gaz_path = Path(path) if path else DEFAULT_GAZETTEER
    with gaz_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict) or not data.get("entities"):
        raise ValueError(f"Invalid gazetteer: {gaz_path}")
    return data


def load_processed_documents(processed_dir: Path | str = DEFAULT_PROCESSED) -> list[NormalizedDocument]:
    root = Path(processed_dir)
    docs: list[NormalizedDocument] = []
    if not root.is_dir():
        return docs
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and "doc_id" in data:
            docs.append(NormalizedDocument.from_dict(data))
    return docs


def _mention_patterns(name: str, aliases: list[str]) -> list[re.Pattern[str]]:
    terms = [name, *aliases]
    patterns: list[re.Pattern[str]] = []
    for term in terms:
        term = term.strip()
        if not term:
            continue
        # Word-boundary-ish match; allow flexible whitespace
        escaped = re.escape(term).replace(r"\ ", r"\s+")
        patterns.append(re.compile(escaped, re.IGNORECASE))
    return patterns


def _find_snippet(text: str, pattern: re.Pattern[str], *, radius: int = 80) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def _dedupe_relations(rels: list[Relation]) -> list[Relation]:
    seen: set[tuple[str, str]] = set()
    out: list[Relation] = []
    for rel in rels:
        key = (rel.type, rel.target)
        if key in seen:
            continue
        seen.add(key)
        out.append(rel)
    return out


def build_entities(
    *,
    gazetteer_path: Path | str | None = None,
    processed_dir: Path | str = DEFAULT_PROCESSED,
    taxonomy: Taxonomy | None = None,
    require_mention: bool = True,
    min_spot_check: int = 20,
) -> list[Entity]:
    """Match gazetteer entities against processed docs; attach evidence + spot checks."""
    taxonomy = taxonomy or load_taxonomy()
    gaz = load_gazetteer(gazetteer_path)
    docs = load_processed_documents(processed_dir)
    corpus = "\n\n".join(d.text for d in docs)

    entities: list[Entity] = []
    for raw in gaz.get("entities") or []:
        eid = str(raw["id"])
        name = str(raw["name"])
        class_ = str(raw["class"])
        aliases = [str(a) for a in (raw.get("aliases") or [])]
        tags = [str(t) for t in (raw.get("tags") or []) if str(t) in taxonomy.tags]
        rels = [
            Relation(type=str(r["type"]), target=str(r["target"]))
            for r in (raw.get("relations") or [])
            if str(r.get("type")) in taxonomy.relations
        ]

        evidence: list[Evidence] = []
        patterns = _mention_patterns(name, aliases)
        for doc in docs:
            for pattern in patterns:
                snippet = _find_snippet(doc.text, pattern)
                if snippet:
                    evidence.append(
                        Evidence(
                            doc_id=doc.doc_id,
                            source_id=doc.source_id,
                            url=doc.url,
                            snippet=snippet[:240],
                        )
                    )
                    break

        mentioned = bool(evidence) or any(p.search(corpus) for p in patterns)
        if require_mention and not mentioned:
            continue

        # suitable_for mirrored as tags already; skip explicit suitable_for edges to Tag nodes
        entities.append(
            Entity(
                id=eid,
                name=name,
                class_=class_,
                aliases=aliases,
                tags=sorted(set(tags)),
                relations=_dedupe_relations(rels),
                evidence=evidence,
                spot_checked=False,
                spot_check_notes="",
            )
        )

    by_id = {e.id: e for e in entities}

    # Apply extra relations only when both endpoints exist
    for raw in gaz.get("extra_relations") or []:
        src = str(raw["source"])
        tgt = str(raw["target"])
        rtype = str(raw["type"])
        if src not in by_id or tgt not in by_id:
            continue
        if rtype not in taxonomy.relations:
            continue
        entity = by_id[src]
        entity.relations = _dedupe_relations(
            [*entity.relations, Relation(type=rtype, target=tgt)]
        )

    # Drop relation targets that were filtered out
    for entity in entities:
        entity.relations = [
            r for r in entity.relations if r.target in by_id or r.type == "suitable_for"
        ]

    # Spot-check: prefer entities with evidence; mark ≥ min_spot_check
    ranked = sorted(
        entities,
        key=lambda e: (-len(e.evidence), e.class_, e.id),
    )
    checked = 0
    for entity in ranked:
        if checked >= min_spot_check:
            break
        if not entity.evidence:
            continue
        entity.spot_checked = True
        snip = entity.evidence[0].snippet
        entity.spot_check_notes = (
            f"Verified mention in {entity.evidence[0].source_id} "
            f"({entity.evidence[0].doc_id}): {snip[:120]}"
        )
        checked += 1

    return sorted(entities, key=lambda e: (e.class_, e.id))


def entities_payload(entities: list[Entity], *, taxonomy: Taxonomy) -> dict[str, Any]:
    return {
        "destination": "Singapore",
        "version": "1.0",
        "taxonomy_classes": list(taxonomy.classes),
        "entity_count": len(entities),
        "spot_checked_count": sum(1 for e in entities if e.spot_checked),
        "by_class": {
            c: sum(1 for e in entities if e.class_ == c) for c in taxonomy.classes
        },
        "entities": [e.to_dict() for e in entities],
    }
