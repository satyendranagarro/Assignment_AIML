"""Orchestrate allowlisted seed crawls with manual-dump fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.crawl.fetch import THIN_BODY_CHARS, SeedFetcher
from src.crawl.store import DEFAULT_MANUAL, DEFAULT_RAW, copy_manual_dumps, save_raw_document
from src.data.models import Source


@dataclass
class SeedRecord:
    source_id: str
    url: str
    ok: bool
    path: str | None = None
    error: str | None = None
    fetch_mode: str = "crawl"
    blocked_by_robots: bool = False
    thin: bool = False


@dataclass
class CrawlResult:
    source_id: str
    seeds: list[SeedRecord] = field(default_factory=list)
    manual_copied: list[str] = field(default_factory=list)
    ok: bool = False
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ok": self.ok,
            "messages": list(self.messages),
            "manual_copied": list(self.manual_copied),
            "seeds": [
                {
                    "url": s.url,
                    "ok": s.ok,
                    "path": s.path,
                    "error": s.error,
                    "fetch_mode": s.fetch_mode,
                    "blocked_by_robots": s.blocked_by_robots,
                    "thin": s.thin,
                }
                for s in self.seeds
            ],
        }


def _defaults_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    defaults = meta.get("defaults") or {}
    return {
        "user_agent": str(
            defaults.get("user_agent")
            or "NAGP-AIML-TravelAssistant/0.1 (educational; contact via repo README)"
        ),
        "respect_robots_txt": bool(defaults.get("respect_robots_txt", True)),
        "request_delay_seconds": float(defaults.get("request_delay_seconds", 1.5)),
    }


def _install_manual(
    result: CrawlResult,
    source: Source,
    *,
    manual_dir: Path | str,
    raw_dir: Path | str,
    reason: str,
) -> bool:
    copied = copy_manual_dumps(source.id, manual_dir=manual_dir, raw_dir=raw_dir)
    result.manual_copied = [str(p) for p in copied]
    if not copied:
        return False
    result.ok = True
    result.messages.append(f"{reason}; installed {len(copied)} manual dump(s)")
    for path in copied:
        result.seeds.append(
            SeedRecord(
                source_id=source.id,
                url=source.citation.url,
                ok=True,
                path=str(path),
                fetch_mode="manual",
            )
        )
    return True


def crawl_source(
    source: Source,
    *,
    fetcher: SeedFetcher,
    raw_dir: Path | str = DEFAULT_RAW,
    manual_dir: Path | str = DEFAULT_MANUAL,
    use_manual_fallback: bool = True,
    force_manual: bool = False,
) -> CrawlResult:
    result = CrawlResult(source_id=source.id)

    if force_manual or source.fetch_mode == "manual":
        if _install_manual(
            result,
            source,
            manual_dir=manual_dir,
            raw_dir=raw_dir,
            reason="Manual mode",
        ):
            return result
        result.messages.append(f"No manual dumps under data/manual/{source.id}/")
        return result

    any_ok = False
    thin_ok = False
    robots_blocked = False
    for seed in source.seed_urls:
        outcome = fetcher.fetch_seed(source, seed)
        if not outcome.ok:
            robots_blocked = robots_blocked or outcome.blocked_by_robots
            result.seeds.append(
                SeedRecord(
                    source_id=source.id,
                    url=seed,
                    ok=False,
                    error=outcome.error,
                    blocked_by_robots=outcome.blocked_by_robots,
                )
            )
            continue

        thin = len(outcome.body.strip()) < THIN_BODY_CHARS
        if thin:
            thin_ok = True
            result.seeds.append(
                SeedRecord(
                    source_id=source.id,
                    url=seed,
                    ok=False,
                    error=f"thin body ({len(outcome.body)} chars)",
                    thin=True,
                    fetch_mode="excerpt" if outcome.used_excerpt else "crawl",
                )
            )
            continue

        path = save_raw_document(
            source_id=source.id,
            url=outcome.url or seed,
            title=outcome.title,
            body=outcome.body,
            topics=list(source.topics),
            extension=outcome.extension,
            fetch_mode="excerpt" if outcome.used_excerpt else "crawl",
            status_code=outcome.status_code,
            content_type=outcome.content_type,
            raw_dir=raw_dir,
        )
        any_ok = True
        result.seeds.append(
            SeedRecord(
                source_id=source.id,
                url=seed,
                ok=True,
                path=str(path),
                fetch_mode="excerpt" if outcome.used_excerpt else "crawl",
            )
        )

    if any_ok:
        result.ok = True
        result.messages.append(f"Fetched {sum(1 for s in result.seeds if s.ok)} seed(s)")
        return result

    if use_manual_fallback:
        if thin_ok:
            reason = "Thin / SPA excerpt"
        elif robots_blocked:
            reason = "Crawl failed (robots/ToS block)"
        else:
            reason = "Crawl failed (fetch failure)"
        if _install_manual(
            result, source, manual_dir=manual_dir, raw_dir=raw_dir, reason=reason
        ):
            return result

    result.messages.append("No successful fetches and no manual fallback available")
    return result


def crawl_all(
    sources: list[Source],
    *,
    meta: dict[str, Any] | None = None,
    raw_dir: Path | str = DEFAULT_RAW,
    manual_dir: Path | str = DEFAULT_MANUAL,
    use_manual_fallback: bool = True,
    force_manual: bool = False,
    source_ids: set[str] | None = None,
    fetcher: SeedFetcher | None = None,
) -> list[CrawlResult]:
    defaults = _defaults_from_meta(meta or {})
    owns = fetcher is None
    active = fetcher or SeedFetcher(
        user_agent=defaults["user_agent"],
        delay_seconds=defaults["request_delay_seconds"],
        respect_robots=defaults["respect_robots_txt"],
    )
    results: list[CrawlResult] = []
    try:
        for source in sorted(sources, key=lambda s: (s.priority, s.id)):
            if source_ids is not None and source.id not in source_ids:
                continue
            results.append(
                crawl_source(
                    source,
                    fetcher=active,
                    raw_dir=raw_dir,
                    manual_dir=manual_dir,
                    use_manual_fallback=use_manual_fallback,
                    force_manual=force_manual,
                )
            )
    finally:
        if owns:
            active.close()
    return results
