#!/usr/bin/env python3
"""Phase 4 — build Chroma KB from processed docs + ontology metadata."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.build import build_kb  # noqa: E402
from src.rag.gate import evaluate_phase4_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Singapore travel Chroma KB")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--entities", type=Path, default=ROOT / "ontology" / "entities.json")
    parser.add_argument("--chroma", type=Path, default=ROOT / "data" / "chroma")
    parser.add_argument(
        "--embeddings",
        default=None,
        help="Embedding provider override (openai|gemini|cursor|fake). Default: EMBEDDING_PROVIDER / LLM_PROVIDER",
    )
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--gate", action="store_true", help="Run Phase 4 gate after build")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        summary = build_kb(
            processed_dir=args.processed,
            entities_path=args.entities,
            chroma_dir=args.chroma,
            embedding_provider=args.embeddings,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            reset=not args.no_reset,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1

    if args.json and not args.gate:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"Built KB: {summary['chunk_count']} chunks from {summary['doc_count']} docs "
            f"→ {args.chroma} (chroma_count={summary['chroma_count']})"
        )
        print(f"  sources: {', '.join(summary['sources'])}")
        print(f"  entities linked: {summary['entity_count']}")

    if args.gate:
        report = evaluate_phase4_gate(
            processed_dir=args.processed,
            entities_path=args.entities,
            chroma_dir=args.chroma,
            rebuild=False,
            force_memory_graph=True,
            embedding_provider=args.embeddings or "fake",
        )
        if args.json:
            print(json.dumps({"build": summary, "gate": report.to_dict()}, indent=2))
        else:
            print("\nGate:")
            for msg in report.messages:
                print(f"  {msg}")
            for err in report.errors:
                print(f"  ! {err}")
        return 0 if report.ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
