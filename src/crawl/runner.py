"""Orchestrate allowlisted BFS crawls with manual-dump fallback."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.crawl.fetch import THIN_BODY_CHARS, SeedFetcher, extract_links, normalize_crawl_url
from src.crawl.store import DEFAULT_MANUAL, DEFAULT_RAW, copy_manual_dumps, save_raw_document
from src.data.models import Source

DEFAULT_MAX_PAGES = 100


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
    depth: int = 0


@dataclass
class CrawlResult:
    source_id: str
    seeds: list[SeedRecord] = field(default_factory=list)
    manual_copied: list[str] = field(default_factory=list)
    ok: bool = False
    messages: list[str] = field(default_factory=list)
    pages_attempted: int = 0
    pages_saved: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "ok": self.ok,
            "messages": list(self.messages),
            "manual_copied": list(self.manual_copied),
            "pages_attempted": self.pages_attempted,
            "pages_saved": self.pages_saved,
            "seeds": [
                {
                    "url": s.url,
                    "ok": s.ok,
                    "path": s.path,
                    "error": s.error,
                    "fetch_mode": s.fetch_mode,
                    "blocked_by_robots": s.blocked_by_robots,
                    "thin": s.thin,
                    "depth": s.depth,
                }
                for s in self.seeds
            ],
        }


def _defaults_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    defaults = meta.get("defaults") or {}
    max_depth_raw = defaults.get("max_depth", None)
    if max_depth_raw is None or max_depth_raw == "" or str(max_depth_raw).lower() == "none":
        max_depth: int | None = None
    else:
        max_depth = int(max_depth_raw)
    return {
        "user_agent": str(
            defaults.get("user_agent")
            or "NAGP-AIML-TravelAssistant/0.1 (educational; contact via repo README)"
        ),
        "respect_robots_txt": bool(defaults.get("respect_robots_txt", True)),
        "request_delay_seconds": float(defaults.get("request_delay_seconds", 1.5)),
        "max_depth": max_depth,
        "max_pages": int(defaults.get("max_pages", DEFAULT_MAX_PAGES)),
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
    max_depth: int | None = None,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> CrawlResult:
    """BFS crawl from seed_urls within allowlist_hosts and Singapore path scope.

    max_depth=None means unbounded depth; max_pages caps attempts per source.
    """
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

    queue: deque[tuple[str, int]] = deque()
    visited: set[str] = set()
    for seed in source.seed_urls:
        normalized = normalize_crawl_url(seed) or seed
        if normalized not in visited:
            visited.add(normalized)
            queue.append((normalized, 0))

    any_ok = False
    thin_ok = False
    robots_blocked = False

    while queue and result.pages_attempted < max_pages:
        url, depth = queue.popleft()
        result.pages_attempted += 1
        outcome = fetcher.fetch_seed(source, url)

        if not outcome.ok:
            robots_blocked = robots_blocked or outcome.blocked_by_robots
            result.seeds.append(
                SeedRecord(
                    source_id=source.id,
                    url=url,
                    ok=False,
                    error=outcome.error,
                    blocked_by_robots=outcome.blocked_by_robots,
                    depth=depth,
                )
            )
            continue

        thin = len(outcome.body.strip()) < THIN_BODY_CHARS
        if thin:
            thin_ok = True
            result.seeds.append(
                SeedRecord(
                    source_id=source.id,
                    url=url,
                    ok=False,
                    error=f"thin body ({len(outcome.body)} chars)",
                    thin=True,
                    fetch_mode="excerpt" if outcome.used_excerpt else "crawl",
                    depth=depth,
                )
            )
            # Still discover links from thin SPA shells when HTML is present.
            html_for_links = outcome.source_html or (
                outcome.body if outcome.body.lstrip().startswith("<") else ""
            )
            _enqueue_links(
                queue,
                visited,
                html=html_for_links,
                base_url=outcome.url or url,
                allowlist=source.allowlist_hosts,
                path_prefixes=source.url_path_prefixes,
                path_contains=source.url_path_contains,
                depth=depth,
                max_depth=max_depth,
                max_pages=max_pages,
            )
            continue

        path = save_raw_document(
            source_id=source.id,
            url=outcome.url or url,
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
        result.pages_saved += 1
        result.seeds.append(
            SeedRecord(
                source_id=source.id,
                url=url,
                ok=True,
                path=str(path),
                fetch_mode="excerpt" if outcome.used_excerpt else "crawl",
                depth=depth,
            )
        )

        html_for_links = outcome.source_html or (
            outcome.body if outcome.body.lstrip().startswith("<") else ""
        )
        _enqueue_links(
            queue,
            visited,
            html=html_for_links,
            base_url=outcome.url or url,
            allowlist=source.allowlist_hosts,
            path_prefixes=source.url_path_prefixes,
            path_contains=source.url_path_contains,
            depth=depth,
            max_depth=max_depth,
            max_pages=max_pages,
        )

    if any_ok:
        result.ok = True
        depth_label = "unbounded" if max_depth is None else str(max_depth)
        result.messages.append(
            f"Fetched {result.pages_saved} page(s) "
            f"(attempted {result.pages_attempted}/{max_pages}, max_depth={depth_label})"
        )
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


def _enqueue_links(
    queue: deque[tuple[str, int]],
    visited: set[str],
    *,
    html: str,
    base_url: str,
    allowlist: tuple[str, ...] | list[str],
    path_prefixes: tuple[str, ...] | list[str] = (),
    path_contains: tuple[str, ...] | list[str] = (),
    depth: int,
    max_depth: int | None,
    max_pages: int,
) -> None:
    next_depth = depth + 1
    if max_depth is not None and next_depth > max_depth:
        return
    for link in extract_links(
        html,
        base_url,
        allowlist=allowlist,
        path_prefixes=path_prefixes,
        path_contains=path_contains,
    ):
        if link in visited:
            continue
        # Cap discovery so the queue cannot grow without bound.
        if len(visited) >= max_pages:
            break
        visited.add(link)
        queue.append((link, next_depth))


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
    max_depth: int | None = None,
    max_pages: int | None = None,
    use_meta_depth: bool = True,
) -> list[CrawlResult]:
    defaults = _defaults_from_meta(meta or {})
    # When use_meta_depth, None max_depth means "read from yaml" (often null=unbounded).
    # Callers that want seeds-only pass max_depth=0 and use_meta_depth=False.
    if use_meta_depth and max_depth is None and meta is not None:
        depth = defaults["max_depth"]
    else:
        depth = max_depth
    pages = defaults["max_pages"] if max_pages is None else max_pages
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
                    max_depth=depth,
                    max_pages=pages,
                )
            )
    finally:
        if owns:
            active.close()
    return results
