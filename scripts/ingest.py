#!/usr/bin/env python3
"""Phase 1 ingest CLI — validate sources + coverage gate; print crawl plan.

Does not fetch the network (crawl is Phase 2). Use this to confirm the registry
before running scripts/crawl.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.coverage import (  # noqa: E402
    evaluate_phase1_gate,
    load_coverage_yaml,
    parse_topics,
    topic_source_index,
)
from src.data.sources import load_and_validate_sources  # noqa: E402


def build_crawl_plan(sources) -> list[dict]:
    plan = []
    for src in sorted(sources, key=lambda s: (s.priority, s.id)):
        plan.append(
            {
                "source_id": src.id,
                "title": src.title,
                "citation": src.citation.to_dict(),
                "priority": src.priority,
                "fetch_mode": src.fetch_mode,
                "seed_urls": list(src.seed_urls),
                "allowlist_hosts": list(src.allowlist_hosts),
                "url_path_prefixes": list(src.url_path_prefixes),
                "url_path_contains": list(src.url_path_contains),
                "topics": list(src.topics),
                "raw_dir": f"data/raw/{src.id}/",
            }
        )
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 1 sources + coverage matrix")
    parser.add_argument(
        "--sources",
        type=Path,
        default=ROOT / "data" / "sources.yaml",
        help="Path to sources.yaml",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=ROOT / "data" / "coverage_matrix.yaml",
        help="Path to coverage_matrix.yaml",
    )
    parser.add_argument(
        "--write-plan",
        type=Path,
        default=None,
        help="Optional path to write crawl plan JSON (e.g. data/processed/crawl_plan.json)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable gate report")
    args = parser.parse_args(argv)

    sources, meta = load_and_validate_sources(args.sources)
    report = evaluate_phase1_gate(sources, matrix_path=args.matrix)
    matrix = load_coverage_yaml(args.matrix)
    topics = parse_topics(matrix)
    index = topic_source_index(sources, topics)
    plan = build_crawl_plan(sources)

    if args.write_plan:
        args.write_plan.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "destination": meta.get("destination", "Singapore"),
            "defaults": meta.get("defaults", {}),
            "plan": plan,
        }
        args.write_plan.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(
            json.dumps(
                {
                    "gate": report.to_dict(),
                    "topic_index": index,
                    "crawl_plan": plan,
                },
                indent=2,
            )
        )
    else:
        print(f"Destination: {meta.get('destination', 'Singapore')}")
        print(f"Sources ({len(sources)}):")
        for src in sources:
            print(f"  - {src.id}: {src.citation.title} <{src.citation.url}>")
        print("\nCoverage (topic → sources):")
        for topic_id, sids in index.items():
            print(f"  - {topic_id}: {', '.join(sids)}")
        print("\nGate:")
        for msg in report.messages:
            print(f"  {msg}")
        if args.write_plan:
            print(f"\nWrote crawl plan → {args.write_plan}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
