#!/usr/bin/env python3
"""Normalize raw dumps under data/raw/<source_id>/ into data/processed/.

Phase 1 ships the normalizer; Phase 2 crawl fills data/raw/. Manual Markdown
dumps (ToS fallback) use the same path layout and optional *.meta.json sidecars:
  { "title": "...", "url": "...", "topics": ["attractions"] }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.normalize import normalize_all_raw  # noqa: E402
from src.data.sources import load_and_validate_sources  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize data/raw → data/processed")
    parser.add_argument(
        "--sources",
        type=Path,
        default=ROOT / "data" / "sources.yaml",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=ROOT / "data" / "raw",
    )
    parser.add_argument(
        "--processed",
        type=Path,
        default=ROOT / "data" / "processed",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    sources, _ = load_and_validate_sources(args.sources)
    docs = normalize_all_raw(sources, raw_dir=args.raw, processed_dir=args.processed)

    summary = {
        "normalized_count": len(docs),
        "by_source": {},
        "docs": [
            {
                "doc_id": d.doc_id,
                "source_id": d.source_id,
                "title": d.title,
                "url": d.url,
                "chars": len(d.text),
            }
            for d in docs
        ],
    }
    for d in docs:
        summary["by_source"][d.source_id] = summary["by_source"].get(d.source_id, 0) + 1

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        if not docs:
            print(
                "No raw files found under data/raw/<source_id>/ "
                "(expected after Phase 2 crawl or a manual dump)."
            )
        else:
            print(f"Normalized {len(docs)} document(s):")
            for d in docs:
                print(f"  - {d.source_id}: {d.title} ({len(d.text)} chars) → {d.doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
