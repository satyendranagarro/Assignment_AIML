"""Load and validate ontology/taxonomy.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAXONOMY = REPO_ROOT / "ontology" / "taxonomy.yaml"


class TaxonomyError(ValueError):
    """Raised when taxonomy.yaml is invalid."""


@dataclass(frozen=True)
class Taxonomy:
    classes: tuple[str, ...]
    relations: tuple[str, ...]
    tags: tuple[str, ...]
    merge_aliases: dict[str, tuple[str, ...]]
    raw: dict[str, Any]


def load_taxonomy(path: Path | str | None = None) -> Taxonomy:
    tax_path = Path(path) if path else DEFAULT_TAXONOMY
    if not tax_path.is_file():
        raise TaxonomyError(f"Taxonomy not found: {tax_path}")
    with tax_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise TaxonomyError("taxonomy.yaml must be a mapping")

    classes = tuple(str(c["id"]) for c in (data.get("classes") or []))
    relations = tuple(str(r["id"]) for r in (data.get("relations") or []))
    tags = tuple(str(t["id"]) for t in (data.get("tags") or []))
    merge_raw = data.get("merge_aliases") or {}
    merge_aliases = {
        str(k): tuple(str(x) for x in (v or [])) for k, v in merge_raw.items()
    }
    return Taxonomy(
        classes=classes,
        relations=relations,
        tags=tags,
        merge_aliases=merge_aliases,
        raw=data,
    )


def validate_taxonomy(taxonomy: Taxonomy) -> list[str]:
    errors: list[str] = []
    required_classes = {
        "Attraction",
        "District",
        "ItineraryDay",
        "TransportMode",
        "Tip",
    }
    required_relations = {"located_in", "suitable_for", "nearby", "part_of_itinerary"}
    required_tags = {"indoor", "outdoor", "family", "culture", "food", "transport"}

    missing_c = required_classes - set(taxonomy.classes)
    missing_r = required_relations - set(taxonomy.relations)
    missing_t = required_tags - set(taxonomy.tags)
    if missing_c:
        errors.append(f"Missing classes: {', '.join(sorted(missing_c))}")
    if missing_r:
        errors.append(f"Missing relations: {', '.join(sorted(missing_r))}")
    if missing_t:
        errors.append(f"Missing tags: {', '.join(sorted(missing_t))}")
    if len(taxonomy.classes) < 5:
        errors.append("Need ≥5 ontology classes")
    return errors
