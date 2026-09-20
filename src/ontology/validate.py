"""Validate extracted entities against taxonomy + JSON schema rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.ontology.models import Entity
from src.ontology.taxonomy import Taxonomy, load_taxonomy

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = REPO_ROOT / "ontology" / "schema.json"


def load_schema(path: Path | str | None = None) -> dict[str, Any]:
    schema_path = Path(path) if path else DEFAULT_SCHEMA
    with schema_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_entities(
    entities: list[Entity],
    *,
    taxonomy: Taxonomy | None = None,
) -> list[str]:
    """Return validation error strings (empty = OK). Does not require jsonschema pkg."""
    taxonomy = taxonomy or load_taxonomy()
    errors: list[str] = []
    ids = [e.id for e in entities]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate entity ids")

    id_set = set(ids)
    for entity in entities:
        if entity.class_ not in taxonomy.classes:
            errors.append(f"{entity.id}: unknown class {entity.class_}")
        for tag in entity.tags:
            if tag not in taxonomy.tags:
                errors.append(f"{entity.id}: unknown tag {tag}")
        for rel in entity.relations:
            if rel.type not in taxonomy.relations:
                errors.append(f"{entity.id}: unknown relation {rel.type}")
            # suitable_for may target tag ids; others should target entity ids
            if rel.type == "suitable_for":
                if rel.target not in taxonomy.tags:
                    errors.append(f"{entity.id}: suitable_for target not a tag: {rel.target}")
            elif rel.target not in id_set:
                errors.append(f"{entity.id}: dangling relation {rel.type}→{rel.target}")
        if not entity.name.strip():
            errors.append(f"{entity.id}: empty name")
        if entity.spot_checked and not entity.evidence:
            errors.append(f"{entity.id}: spot_checked but no evidence")

    return errors
