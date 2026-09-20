#!/usr/bin/env python3
"""Phase 4 — load ontology entities into Neo4j (falls back to memory dry-run)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.store import InMemoryGraphStore, Neo4jGraphStore, open_graph_store  # noqa: E402
from src.ontology.gate import load_entities_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load ontology entities into Neo4j")
    parser.add_argument("--entities", type=Path, default=ROOT / "ontology" / "entities.json")
    parser.add_argument(
        "--memory",
        action="store_true",
        help="Force in-memory graph (no Neo4j connection)",
    )
    parser.add_argument(
        "--require-neo4j",
        action="store_true",
        help="Fail if Neo4j is unreachable (do not fall back to memory)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.entities.is_file():
        print(f"Missing entities file: {args.entities}", file=sys.stderr)
        return 1

    entities = load_entities_file(args.entities)
    if args.memory:
        store = InMemoryGraphStore()
    elif args.require_neo4j:
        try:
            store = Neo4jGraphStore()
        except Exception as exc:  # noqa: BLE001
            print(f"Neo4j required but unavailable: {exc}", file=sys.stderr)
            return 1
    else:
        store = open_graph_store(prefer_neo4j=True)

    stats = store.load_entities(entities, reset=True)
    store.close()

    payload = stats.to_dict()
    payload["loaded"] = len(entities)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"Loaded {payload['loaded']} entities / {payload['relation_count']} relations "
            f"via backend={payload['backend']}"
        )
        for cls, n in sorted(payload["by_class"].items()):
            print(f"  {cls}: {n}")
        if payload["backend"] == "memory" and not args.memory:
            print(
                "  (Neo4j not configured/reachable — used in-memory. "
                "Set NEO4J_PASSWORD and start Neo4j, or pass --memory.)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
