"""Phase 3 exit gate: taxonomy valid + ≥20 spot-checked entities with evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.ontology.extract import build_entities, entities_payload
from src.ontology.models import Entity
from src.ontology.taxonomy import load_taxonomy, validate_taxonomy
from src.ontology.validate import validate_entities

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENTITIES = REPO_ROOT / "ontology" / "entities.json"
MIN_SPOT_CHECKED = 20
MIN_ENTITIES = 20


@dataclass
class Phase3GateReport:
    ok: bool
    entity_count: int
    spot_checked: int
    class_counts: dict[str, int]
    taxonomy_errors: list[str] = field(default_factory=list)
    entity_errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "entity_count": self.entity_count,
            "spot_checked": self.spot_checked,
            "class_counts": dict(self.class_counts),
            "taxonomy_errors": list(self.taxonomy_errors),
            "entity_errors": list(self.entity_errors),
            "messages": list(self.messages),
        }


def load_entities_file(path: Path | str = DEFAULT_ENTITIES) -> list[Entity]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Entity.from_dict(item) for item in data.get("entities") or []]


def evaluate_phase3_gate(
    entities: list[Entity] | None = None,
    *,
    entities_path: Path | str | None = None,
    taxonomy_path: Path | str | None = None,
    min_spot_checked: int = MIN_SPOT_CHECKED,
    min_entities: int = MIN_ENTITIES,
) -> Phase3GateReport:
    taxonomy = load_taxonomy(taxonomy_path)
    tax_errors = validate_taxonomy(taxonomy)

    if entities is None:
        path = Path(entities_path) if entities_path else DEFAULT_ENTITIES
        if path.is_file():
            entities = load_entities_file(path)
        else:
            entities = []

    ent_errors = validate_entities(entities, taxonomy=taxonomy)
    spot = sum(1 for e in entities if e.spot_checked)
    class_counts = {c: sum(1 for e in entities if e.class_ == c) for c in taxonomy.classes}
    missing_classes = [c for c, n in class_counts.items() if n < 1]

    messages: list[str] = []
    if not tax_errors:
        messages.append("Taxonomy OK (classes, relations, tags)")
    else:
        messages.append("Taxonomy FAIL: " + "; ".join(tax_errors))

    if len(entities) >= min_entities:
        messages.append(f"Entity count OK ({len(entities)} ≥ {min_entities})")
    else:
        messages.append(f"Entity count FAIL ({len(entities)} < {min_entities})")

    if spot >= min_spot_checked:
        messages.append(f"Spot-check OK ({spot} ≥ {min_spot_checked})")
    else:
        messages.append(f"Spot-check FAIL ({spot} < {min_spot_checked})")

    if missing_classes:
        messages.append(f"Missing class coverage: {', '.join(missing_classes)}")
        ent_errors = [*ent_errors, f"no entities for classes: {', '.join(missing_classes)}"]
    else:
        messages.append("All taxonomy classes have ≥1 entity")

    if ent_errors:
        messages.append(f"Entity validation errors: {len(ent_errors)}")

    ok = (
        not tax_errors
        and not ent_errors
        and len(entities) >= min_entities
        and spot >= min_spot_checked
        and not missing_classes
    )
    if ok:
        messages.append(
            "Phase 3 gate PASS — dense named entities → prefer hybrid GraphRAG in Phase 4"
        )
    else:
        messages.append("Phase 3 gate FAIL — fix taxonomy/entities before stores")

    return Phase3GateReport(
        ok=ok,
        entity_count=len(entities),
        spot_checked=spot,
        class_counts=class_counts,
        taxonomy_errors=tax_errors,
        entity_errors=ent_errors,
        messages=messages,
    )


def write_entities_json(
    entities: list[Entity],
    path: Path | str = DEFAULT_ENTITIES,
    *,
    taxonomy_path: Path | str | None = None,
) -> Path:
    taxonomy = load_taxonomy(taxonomy_path)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = entities_payload(entities, taxonomy=taxonomy)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
