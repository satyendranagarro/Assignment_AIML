#!/usr/bin/env python3
"""Phase 4 — retrieval smoke / eval over Chroma (+ optional graph)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.store import InMemoryGraphStore, open_graph_store  # noqa: E402
from src.llm.factory import get_embeddings  # noqa: E402
from src.ontology.gate import load_entities_file  # noqa: E402
from src.rag.chroma_store import load_chroma  # noqa: E402
from src.rag.gate import SMOKE_QUERIES, evaluate_phase4_gate  # noqa: E402
from src.rag.retrieve import HybridRetriever  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Singapore KB retrieval")
    parser.add_argument("--chroma", type=Path, default=ROOT / "data" / "chroma")
    parser.add_argument("--entities", type=Path, default=ROOT / "ontology" / "entities.json")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--embeddings", default="fake")
    parser.add_argument("--query", action="append", default=[], help="Custom query (repeatable)")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--gate", action="store_true", help="Run full Phase 4 gate")
    parser.add_argument("--memory-graph", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.gate:
        report = evaluate_phase4_gate(
            processed_dir=args.processed,
            entities_path=args.entities,
            chroma_dir=args.chroma,
            rebuild=True,
            force_memory_graph=True,
            embedding_provider=args.embeddings,
        )
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            for msg in report.messages:
                print(msg)
            for err in report.errors:
                print("!", err)
        return 0 if report.ok else 1

    if not args.chroma.is_dir() or not any(args.chroma.iterdir()):
        print(
            f"Chroma empty at {args.chroma}. Run: python scripts/build_kb.py --embeddings fake",
            file=sys.stderr,
        )
        return 1

    embeddings = get_embeddings(args.embeddings)
    store = load_chroma(embeddings=embeddings, persist_dir=args.chroma)
    graph = InMemoryGraphStore() if args.memory_graph else open_graph_store()
    if args.entities.is_file():
        graph.load_entities(load_entities_file(args.entities), reset=True)

    queries = args.query or list(SMOKE_QUERIES)
    retriever = HybridRetriever(store, graph, chroma_k=args.k)
    results = []
    for q in queries:
        hits = retriever.retrieve(q, k=args.k)
        entry = {
            "query": q,
            "hit_count": len(hits),
            "hits": [
                {
                    "source": h.source,
                    "score": round(h.score, 4),
                    "title": h.title,
                    "url": h.url,
                    "entity_id": h.entity_id,
                    "preview": h.text[:160],
                }
                for h in hits
            ],
        }
        results.append(entry)

    graph.close()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for entry in results:
            print(f"\nQuery: {entry['query']} ({entry['hit_count']} hits)")
            for h in entry["hits"]:
                label = h["entity_id"] or h["title"] or "(chunk)"
                print(f"  [{h['source']}] {label} score={h['score']}")
                if h["url"]:
                    print(f"    {h['url']}")
                print(f"    {h['preview'][:120]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
