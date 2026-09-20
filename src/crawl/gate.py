"""Phase 2 exit gate: topic buckets green + reproducible raw/manual content."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.crawl.buckets import BucketReport, evaluate_topic_buckets
from src.crawl.store import DEFAULT_MANUAL, list_manual_sources
from src.data.models import Source
from src.data.normalize import DEFAULT_PROCESSED, DEFAULT_RAW, iter_raw_files
from src.data.sources import load_and_validate_sources


@dataclass
class Phase2GateReport:
    ok: bool
    bucket_report: BucketReport
    sources_with_raw: list[str] = field(default_factory=list)
    sources_missing_content: list[str] = field(default_factory=list)
    manual_sources: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "sources_with_raw": list(self.sources_with_raw),
            "sources_missing_content": list(self.sources_missing_content),
            "manual_sources": list(self.manual_sources),
            "messages": list(self.messages),
            "buckets": self.bucket_report.to_dict(),
        }


def _sources_with_files(raw_dir: Path, sources: list[Source]) -> tuple[list[str], list[str]]:
    present: set[str] = set()
    for path in iter_raw_files(raw_dir):
        try:
            rel = path.relative_to(raw_dir)
            if rel.parts:
                present.add(rel.parts[0])
        except ValueError:
            continue
    with_raw = sorted(s.id for s in sources if s.id in present)
    missing = sorted(s.id for s in sources if s.id not in present)
    return with_raw, missing


def evaluate_phase2_gate(
    sources: list[Source] | None = None,
    *,
    sources_path: Path | str | None = None,
    matrix_path: Path | str | None = None,
    raw_dir: Path | str = DEFAULT_RAW,
    processed_dir: Path | str = DEFAULT_PROCESSED,
    manual_dir: Path | str = DEFAULT_MANUAL,
) -> Phase2GateReport:
    if sources is None:
        sources, _ = load_and_validate_sources(sources_path)

    bucket_report = evaluate_topic_buckets(
        sources,
        matrix_path=matrix_path,
        processed_dir=processed_dir,
        raw_dir=raw_dir,
    )
    with_raw, missing = _sources_with_files(Path(raw_dir), sources)
    manuals = list_manual_sources(manual_dir)

    messages = list(bucket_report.messages)
    if with_raw:
        messages.append(f"Raw content present for: {', '.join(with_raw)}")
    if missing:
        messages.append(f"Sources still missing raw files: {', '.join(missing)}")
    if manuals:
        messages.append(f"Manual fallback packs: {', '.join(manuals)}")

    # Gate: all required topics green AND every registered source has at least one raw file
    content_ok = len(missing) == 0 and len(with_raw) >= 3
    ok = bucket_report.ok and content_ok
    if ok:
        messages.append("Phase 2 gate PASS — proceed to Phase 3 ontology")
    else:
        messages.append("Phase 2 gate FAIL — expand seeds, add manual dumps, or re-normalize")

    return Phase2GateReport(
        ok=ok,
        bucket_report=bucket_report,
        sources_with_raw=with_raw,
        sources_missing_content=missing,
        manual_sources=manuals,
        messages=messages,
    )
