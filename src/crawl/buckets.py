"""Topic bucket evaluation from normalized / raw content."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.data.coverage import TopicCoverage, load_coverage_yaml, parse_topics
from src.data.models import NormalizedDocument, Source
from src.data.normalize import DEFAULT_PROCESSED, iter_raw_files, normalize_raw_payload
from src.data.sources import sources_by_id

# Char thresholds for required-topic buckets (after normalize).
GREEN_MIN_CHARS = 800
YELLOW_MIN_CHARS = 200


@dataclass
class TopicBucket:
    topic_id: str
    required: bool
    status: str  # green | yellow | red | planned
    doc_count: int
    char_count: int
    covering_sources: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "required": self.required,
            "status": self.status,
            "doc_count": self.doc_count,
            "char_count": self.char_count,
            "covering_sources": list(self.covering_sources),
            "notes": self.notes,
        }


@dataclass
class BucketReport:
    buckets: list[TopicBucket]
    green_required: int
    yellow_required: int
    red_required: int
    ok: bool
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "green_required": self.green_required,
            "yellow_required": self.yellow_required,
            "red_required": self.red_required,
            "messages": list(self.messages),
            "buckets": [b.to_dict() for b in self.buckets],
        }


def _load_processed_docs(processed_dir: Path) -> list[NormalizedDocument]:
    docs: list[NormalizedDocument] = []
    if not processed_dir.is_dir():
        return docs
    for path in sorted(processed_dir.rglob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "doc_id" not in data:
            continue
        docs.append(NormalizedDocument.from_dict(data))
    return docs


def _docs_for_topic(
    topic: TopicCoverage,
    docs: list[NormalizedDocument],
) -> list[NormalizedDocument]:
    """Any normalized doc from a matrix `covered_by` source counts toward the topic.

    Matrix ids (e.g. neighbourhoods, cultural_practical) may differ from source topic
    tags (districts, practical); coverage is intentional via covered_by, not tag equality.
    """
    covering = set(topic.covered_by)
    matched: list[NormalizedDocument] = []
    for doc in docs:
        if doc.source_id in covering:
            matched.append(doc)
            continue
        if topic.id in set(doc.topics):
            matched.append(doc)
    return matched


def classify_chars(char_count: int, *, doc_count: int) -> str:
    if doc_count < 1 or char_count < YELLOW_MIN_CHARS:
        return "red"
    if char_count >= GREEN_MIN_CHARS:
        return "green"
    return "yellow"


def evaluate_topic_buckets(
    sources: list[Source],
    *,
    matrix_path: Path | str | None = None,
    processed_dir: Path | str = DEFAULT_PROCESSED,
    raw_dir: Path | str | None = None,
    green_min: int = GREEN_MIN_CHARS,
    yellow_min: int = YELLOW_MIN_CHARS,
) -> BucketReport:
    """Score each coverage-matrix topic from processed docs (raw fallback if empty)."""
    matrix = load_coverage_yaml(matrix_path)
    topics = parse_topics(matrix)
    by_id = sources_by_id(sources)
    docs = _load_processed_docs(Path(processed_dir))

    # If nothing normalized yet, attempt light in-memory normalize from raw for scoring only.
    if not docs and raw_dir is not None:
        from src.data.normalize import load_sidecar_meta

        for path in iter_raw_files(raw_dir):
            try:
                rel = path.relative_to(Path(raw_dir))
                source_id = rel.parts[0]
            except ValueError:
                continue
            source = by_id.get(source_id)
            if source is None:
                continue
            meta = load_sidecar_meta(path)
            raw = path.read_text(encoding="utf-8", errors="replace")
            title = str(meta.get("title") or source.citation.title)
            url = str(meta.get("url") or source.citation.url)
            topics_meta = meta.get("topics")
            try:
                if path.suffix.lower() in {".html", ".htm"}:
                    docs.append(
                        normalize_raw_payload(
                            source=source, html=raw, title=title, url=url, topics=topics_meta
                        )
                    )
                else:
                    docs.append(
                        normalize_raw_payload(
                            source=source, text=raw, title=title, url=url, topics=topics_meta
                        )
                    )
            except ValueError:
                continue

    buckets: list[TopicBucket] = []
    for topic in topics:
        matched = _docs_for_topic(topic, docs)
        # Deduplicate by doc_id
        uniq: dict[str, NormalizedDocument] = {d.doc_id: d for d in matched}
        matched_list = list(uniq.values())
        chars = sum(len(d.text) for d in matched_list)
        if len(matched_list) < 1 or chars < yellow_min:
            status = "red"
        elif chars >= green_min:
            status = "green"
        else:
            status = "yellow"
        buckets.append(
            TopicBucket(
                topic_id=topic.id,
                required=topic.required,
                status=status,
                doc_count=len(matched_list),
                char_count=chars,
                covering_sources=list(topic.covered_by),
                notes=topic.notes,
            )
        )

    required = [b for b in buckets if b.required]
    green_r = sum(1 for b in required if b.status == "green")
    yellow_r = sum(1 for b in required if b.status == "yellow")
    red_r = sum(1 for b in required if b.status == "red")
    ok = red_r == 0 and yellow_r == 0 and green_r == len(required) and len(required) > 0

    messages = [
        f"Required topics: {green_r} green, {yellow_r} yellow, {red_r} red (of {len(required)})"
    ]
    if ok:
        messages.append("Phase 2 topic buckets PASS (all required green)")
    else:
        weak = [b.topic_id for b in required if b.status != "green"]
        messages.append(f"Weak / missing required topics: {', '.join(weak)}")

    return BucketReport(
        buckets=buckets,
        green_required=green_r,
        yellow_required=yellow_r,
        red_required=red_r,
        ok=ok,
        messages=messages,
    )


def update_matrix_statuses(
    report: BucketReport,
    *,
    matrix_path: Path | str,
) -> Path:
    """Write bucket statuses back into coverage_matrix.yaml."""
    path = Path(matrix_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    status_by_id = {b.topic_id: b.status for b in report.buckets}
    for item in data.get("topics") or []:
        tid = item.get("id")
        if tid in status_by_id:
            item["status"] = status_by_id[tid]
    # Refresh gate section notes for phase 2
    gate = data.setdefault("gate", {})
    gate["phase_2_exit"] = {
        "description": "All required topic buckets green; crawl reproducible via seeds + manual fallback",
        "checks": ["required_topics_green", "raw_or_manual_present"],
        "last_bucket_summary": {
            "green_required": report.green_required,
            "yellow_required": report.yellow_required,
            "red_required": report.red_required,
            "ok": report.ok,
        },
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
