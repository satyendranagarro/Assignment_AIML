#!/usr/bin/env python3
"""Phase 2 crawl CLI — allowlisted BFS crawl → data/raw/ + topic bucket gate.

Reproducible path:
  1. BFS from each source's seed_urls (allowlist + robots + delay; max_depth/max_pages)
  2. On robots/HTTP failure, install committed dumps from data/manual/<source_id>/
  3. Normalize raw → processed, score topic buckets, optionally update coverage_matrix.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.crawl.buckets import evaluate_topic_buckets, update_matrix_statuses  # noqa: E402
from src.crawl.gate import evaluate_phase2_gate  # noqa: E402
from src.crawl.runner import DEFAULT_MAX_PAGES, crawl_all  # noqa: E402
from src.data.normalize import normalize_all_raw  # noqa: E402
from src.data.sources import load_and_validate_sources  # noqa: E402


def _parse_max_depth(value: str | None) -> int | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"", "none", "null", "unbounded"}:
        return None
    return int(lowered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2 allowlisted BFS crawl + topic buckets")
    parser.add_argument("--sources", type=Path, default=ROOT / "data" / "sources.yaml")
    parser.add_argument("--matrix", type=Path, default=ROOT / "data" / "coverage_matrix.yaml")
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--processed", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--manual", type=Path, default=ROOT / "data" / "manual")
    parser.add_argument(
        "--source-id",
        action="append",
        dest="source_ids",
        default=None,
        help="Limit crawl to one or more source ids (repeatable)",
    )
    parser.add_argument(
        "--max-depth",
        type=str,
        default=None,
        help="BFS depth cap (0=seeds only). Omit or 'none' = unbounded (yaml default).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=f"Max pages attempted per source (default from yaml or {DEFAULT_MAX_PAGES})",
    )
    parser.add_argument(
        "--force-manual",
        action="store_true",
        help="Skip network; install data/manual dumps only",
    )
    parser.add_argument(
        "--no-manual-fallback",
        action="store_true",
        help="Do not copy manual dumps when fetch fails",
    )
    parser.add_argument(
        "--skip-normalize",
        action="store_true",
        help="Crawl only; do not run normalize / bucket update",
    )
    parser.add_argument(
        "--update-matrix",
        action="store_true",
        help="Write topic statuses back to coverage_matrix.yaml",
    )
    parser.add_argument(
        "--gate-only",
        action="store_true",
        help="Evaluate Phase 2 gate on existing raw/processed (no fetch)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    sources, meta = load_and_validate_sources(args.sources)
    source_ids = set(args.source_ids) if args.source_ids else None
    # CLI omit → read yaml (null=unbounded). Explicit --max-depth 0 = seeds only.
    cli_depth = _parse_max_depth(args.max_depth) if args.max_depth is not None else None
    use_meta_depth = args.max_depth is None

    crawl_results = []
    if not args.gate_only:
        crawl_results = crawl_all(
            sources,
            meta=meta,
            raw_dir=args.raw,
            manual_dir=args.manual,
            use_manual_fallback=not args.no_manual_fallback,
            force_manual=args.force_manual,
            source_ids=source_ids,
            max_depth=cli_depth,
            max_pages=args.max_pages,
            use_meta_depth=use_meta_depth,
        )

    docs = []
    if not args.gate_only and not args.skip_normalize:
        docs = normalize_all_raw(sources, raw_dir=args.raw, processed_dir=args.processed)

    bucket_report = evaluate_topic_buckets(
        sources,
        matrix_path=args.matrix,
        processed_dir=args.processed,
        raw_dir=args.raw,
    )
    if args.update_matrix and not args.gate_only:
        update_matrix_statuses(bucket_report, matrix_path=args.matrix)

    gate = evaluate_phase2_gate(
        sources,
        matrix_path=args.matrix,
        raw_dir=args.raw,
        processed_dir=args.processed,
        manual_dir=args.manual,
    )

    payload = {
        "crawl": [r.to_dict() for r in crawl_results],
        "normalized_count": len(docs),
        "buckets": bucket_report.to_dict(),
        "gate": gate.to_dict(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if crawl_results:
            print("Crawl:")
            for r in crawl_results:
                status = "OK" if r.ok else "FAIL"
                print(f"  [{status}] {r.source_id}: {'; '.join(r.messages)}")
                for seed in r.seeds:
                    mark = "✓" if seed.ok else "✗"
                    detail = seed.path or seed.error or ""
                    print(f"      {mark} {seed.url} ({seed.fetch_mode}) {detail}")
        if docs:
            print(f"\nNormalized {len(docs)} document(s)")
        print("\nTopic buckets:")
        for b in bucket_report.buckets:
            req = "required" if b.required else "optional"
            print(
                f"  - {b.topic_id}: {b.status} ({req}, {b.doc_count} docs, {b.char_count} chars)"
            )
        print("\nGate:")
        for msg in gate.messages:
            print(f"  {msg}")
        if args.update_matrix and not args.gate_only:
            print(f"\nUpdated matrix statuses → {args.matrix}")

    return 0 if gate.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
