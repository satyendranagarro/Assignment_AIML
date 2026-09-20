#!/usr/bin/env python3
"""Phase 3 ontology CLI — extract entities from processed docs + gazetteer.

Writes ontology/entities.json and evaluates the Phase 3 gate (≥20 spot-checked).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ontology.extract import build_entities  # noqa: E402
from src.ontology.gate import evaluate_phase3_gate, write_entities_json  # noqa: E402
from src.ontology.taxonomy import load_taxonomy, validate_taxonomy  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Singapore travel ontology entities")
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "ontology" / "taxonomy.yaml")
    parser.add_argument("--gazetteer", type=Path, default=ROOT / "ontology" / "gazetteer.yaml")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--out", type=Path, default=ROOT / "ontology" / "entities.json")
    parser.add_argument("--min-spot-check", type=int, default=20)
    parser.add_argument(
        "--gate-only",
        action="store_true",
        help="Evaluate existing ontology/entities.json without rebuilding",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    taxonomy = load_taxonomy(args.taxonomy)
    tax_errors = validate_taxonomy(taxonomy)
    if tax_errors and not args.gate_only:
        print("Taxonomy errors:", *tax_errors, sep="\n  ")
        return 1

    entities = []
    if not args.gate_only:
        if not any(Path(args.processed).rglob("*.json")):
            print(
                f"No processed docs under {args.processed}. "
                "Run: python scripts/crawl.py --force-manual && python scripts/normalize.py"
            )
            return 1
        entities = build_entities(
            gazetteer_path=args.gazetteer,
            processed_dir=args.processed,
            taxonomy=taxonomy,
            min_spot_check=args.min_spot_check,
        )
        write_entities_json(entities, args.out, taxonomy_path=args.taxonomy)

    gate = evaluate_phase3_gate(
        entities if entities else None,
        entities_path=args.out,
        taxonomy_path=args.taxonomy,
        min_spot_checked=args.min_spot_check,
    )

    if args.json:
        print(json.dumps(gate.to_dict(), indent=2))
    else:
        if not args.gate_only:
            print(f"Wrote {len(entities)} entities → {args.out}")
            by = gate.class_counts
            for cls, n in by.items():
                print(f"  {cls}: {n}")
        print("\nGate:")
        for msg in gate.messages:
            print(f"  {msg}")
        if gate.entity_errors:
            for err in gate.entity_errors[:10]:
                print(f"  ! {err}")

    return 0 if gate.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
