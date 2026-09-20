"""Load and validate Phase 1 source registry (`data/sources.yaml`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from src.data.models import Source

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = REPO_ROOT / "data" / "sources.yaml"


class SourceRegistryError(ValueError):
    """Raised when the source registry fails validation."""


def load_sources_yaml(path: Path | str | None = None) -> dict[str, Any]:
    sources_path = Path(path) if path else DEFAULT_SOURCES_PATH
    if not sources_path.is_file():
        raise SourceRegistryError(f"Sources file not found: {sources_path}")
    with sources_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise SourceRegistryError("sources.yaml must be a mapping at the top level")
    return data


def parse_sources(data: dict[str, Any]) -> list[Source]:
    raw_sources = data.get("sources") or []
    if not isinstance(raw_sources, list) or not raw_sources:
        raise SourceRegistryError("sources.yaml must define a non-empty 'sources' list")
    return [Source.from_dict(item) for item in raw_sources]


def validate_sources(sources: list[Source], *, min_count: int = 3) -> list[str]:
    """Return a list of validation error strings (empty = OK)."""
    errors: list[str] = []
    if len(sources) < min_count:
        errors.append(f"Need ≥{min_count} sources; found {len(sources)}")

    seen_ids: set[str] = set()
    for src in sources:
        if not src.id:
            errors.append("Source missing id")
            continue
        if src.id in seen_ids:
            errors.append(f"Duplicate source id: {src.id}")
        seen_ids.add(src.id)

        if not src.title.strip():
            errors.append(f"{src.id}: missing title")
        if not src.url.strip():
            errors.append(f"{src.id}: missing url")
        else:
            parsed = urlparse(src.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{src.id}: invalid url {src.url!r}")

        if not src.citation.title.strip() or not src.citation.url.strip():
            errors.append(f"{src.id}: citation must include title and url")

        if not src.seed_urls:
            errors.append(f"{src.id}: at least one seed_url required")

        if not src.topics:
            errors.append(f"{src.id}: at least one topic tag required")

    return errors


def load_and_validate_sources(
    path: Path | str | None = None, *, min_count: int = 3
) -> tuple[list[Source], dict[str, Any]]:
    data = load_sources_yaml(path)
    sources = parse_sources(data)
    errors = validate_sources(sources, min_count=min_count)
    if errors:
        raise SourceRegistryError("; ".join(errors))
    return sources, data


def sources_by_id(sources: list[Source]) -> dict[str, Source]:
    return {s.id: s for s in sources}
