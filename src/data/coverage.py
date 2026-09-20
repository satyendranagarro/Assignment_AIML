"""Coverage matrix load + Phase 1 gate checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.data.models import Source
from src.data.sources import load_and_validate_sources, sources_by_id

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX_PATH = REPO_ROOT / "data" / "coverage_matrix.yaml"


class CoverageError(ValueError):
    """Raised when the coverage matrix fails validation or gate checks."""


@dataclass(frozen=True)
class TopicCoverage:
    id: str
    label: str
    required: bool
    covered_by: tuple[str, ...]
    status: str
    notes: str = ""
    assignment_ref: str = ""


@dataclass
class GateReport:
    ok: bool
    source_count: int
    required_topics: int
    unmapped_required: list[str]
    unknown_source_refs: list[str]
    citation_errors: list[str]
    messages: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source_count": self.source_count,
            "required_topics": self.required_topics,
            "unmapped_required": list(self.unmapped_required),
            "unknown_source_refs": list(self.unknown_source_refs),
            "citation_errors": list(self.citation_errors),
            "messages": list(self.messages),
        }


def load_coverage_yaml(path: Path | str | None = None) -> dict[str, Any]:
    matrix_path = Path(path) if path else DEFAULT_MATRIX_PATH
    if not matrix_path.is_file():
        raise CoverageError(f"Coverage matrix not found: {matrix_path}")
    with matrix_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise CoverageError("coverage_matrix.yaml must be a mapping at the top level")
    return data


def parse_topics(data: dict[str, Any]) -> list[TopicCoverage]:
    raw_topics = data.get("topics") or []
    if not isinstance(raw_topics, list) or not raw_topics:
        raise CoverageError("coverage_matrix.yaml must define a non-empty 'topics' list")
    topics: list[TopicCoverage] = []
    for item in raw_topics:
        topics.append(
            TopicCoverage(
                id=str(item["id"]),
                label=str(item.get("label") or item["id"]),
                required=bool(item.get("required", False)),
                covered_by=tuple(item.get("covered_by") or ()),
                status=str(item.get("status", "planned")),
                notes=str(item.get("notes", "")),
                assignment_ref=str(item.get("assignment_ref", "")),
            )
        )
    return topics


def evaluate_phase1_gate(
    sources: list[Source] | None = None,
    *,
    sources_path: Path | str | None = None,
    matrix_path: Path | str | None = None,
) -> GateReport:
    if sources is None:
        sources, _ = load_and_validate_sources(sources_path)
    matrix = load_coverage_yaml(matrix_path)
    topics = parse_topics(matrix)
    min_sources = int(matrix.get("min_sources_required", 3))

    by_id = sources_by_id(sources)
    messages: list[str] = []
    unmapped: list[str] = []
    unknown_refs: list[str] = []
    citation_errors: list[str] = []

    for src in sources:
        if not src.citation.title or not src.citation.url:
            citation_errors.append(src.id)

    required = [t for t in topics if t.required]
    for topic in required:
        if not topic.covered_by:
            unmapped.append(topic.id)
            continue
        missing = [sid for sid in topic.covered_by if sid not in by_id]
        if missing:
            unknown_refs.extend(f"{topic.id}->{sid}" for sid in missing)
        if all(sid not in by_id for sid in topic.covered_by):
            unmapped.append(topic.id)

    # Also flag any covered_by refs on optional topics that don't exist
    for topic in topics:
        for sid in topic.covered_by:
            if sid not in by_id and f"{topic.id}->{sid}" not in unknown_refs:
                unknown_refs.append(f"{topic.id}->{sid}")

    ok = (
        len(sources) >= min_sources
        and not unmapped
        and not unknown_refs
        and not citation_errors
    )

    if len(sources) >= min_sources:
        messages.append(f"Source count OK ({len(sources)} ≥ {min_sources})")
    else:
        messages.append(f"Source count FAIL ({len(sources)} < {min_sources})")

    if not unmapped:
        messages.append(f"All {len(required)} required topics mapped")
    else:
        messages.append(f"Unmapped required topics: {', '.join(unmapped)}")

    if unknown_refs:
        messages.append(f"Unknown source refs: {', '.join(unknown_refs)}")
    if citation_errors:
        messages.append(f"Citation incomplete: {', '.join(citation_errors)}")

    if ok:
        messages.append(
            "Phase 1 gate PASS — proceed to Phase 2 crawl (topics still status=planned until content lands)"
        )
    else:
        messages.append("Phase 1 gate FAIL — fix registry/matrix before crawl")

    return GateReport(
        ok=ok,
        source_count=len(sources),
        required_topics=len(required),
        unmapped_required=unmapped,
        unknown_source_refs=unknown_refs,
        citation_errors=citation_errors,
        messages=messages,
    )


def topic_source_index(
    sources: list[Source], topics: list[TopicCoverage]
) -> dict[str, list[str]]:
    """Map topic id → source ids (union of matrix covered_by and source.topics)."""
    index: dict[str, set[str]] = {t.id: set(t.covered_by) for t in topics}
    for src in sources:
        for topic in src.topics:
            index.setdefault(topic, set()).add(src.id)
    return {k: sorted(v) for k, v in sorted(index.items())}
