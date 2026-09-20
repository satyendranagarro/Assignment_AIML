"""Phase 2 crawl unit tests (mocked network; uses committed manual dumps)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import httpx

from src.crawl.buckets import evaluate_topic_buckets, update_matrix_statuses
from src.crawl.fetch import SeedFetcher, host_allowed, html_to_excerpt, prefers_excerpt
from src.crawl.gate import evaluate_phase2_gate
from src.crawl.runner import crawl_all, crawl_source
from src.crawl.store import copy_manual_dumps, save_raw_document
from src.data.models import Citation, Source
from src.data.normalize import normalize_all_raw
from src.data.sources import load_and_validate_sources

ROOT = Path(__file__).resolve().parents[1]


def _sample_source(**overrides) -> Source:
    base = dict(
        id="demo-source",
        title="Demo",
        url="https://example.com/page",
        publisher="Demo",
        license="CC BY-SA 4.0",
        reuse_notes="",
        fetch_mode="crawl",
        priority=1,
        topics=("attractions", "transport"),
        seed_urls=("https://example.com/page",),
        allowlist_hosts=("example.com",),
        citation=Citation(title="Demo", url="https://example.com/page"),
    )
    base.update(overrides)
    return Source(**base)


def test_host_allowed_matches_www_variants():
    assert host_allowed("https://www.example.com/a", ["example.com"])
    assert host_allowed("https://example.com/a", ["www.example.com"])
    assert not host_allowed("https://evil.com/a", ["example.com"])


def test_prefers_excerpt_for_arr_license():
    src = _sample_source(license="All rights reserved — fair educational excerpt only")
    assert prefers_excerpt(src)
    assert not prefers_excerpt(_sample_source())


def test_html_to_excerpt_strips_scripts_and_caps():
    html = "<html><body><script>x()</script><p>" + ("word " * 5000) + "</p></body></html>"
    text = html_to_excerpt(html, max_chars=200)
    assert "x()" not in text
    assert "Excerpt truncated" in text
    assert len(text) < 400


def test_save_raw_and_sidecar(tmp_path: Path):
    path = save_raw_document(
        source_id="demo",
        url="https://example.com/hello",
        title="Hello",
        body="<html><body>Hi</body></html>",
        topics=["attractions"],
        raw_dir=tmp_path,
    )
    assert path.is_file()
    meta = path.parent / f"{path.name}.meta.json"
    assert meta.is_file()
    assert "Hello" in meta.read_text(encoding="utf-8")


def test_copy_manual_dumps_from_repo(tmp_path: Path):
    copied = copy_manual_dumps(
        "visitsg-essentials",
        manual_dir=ROOT / "data" / "manual",
        raw_dir=tmp_path,
    )
    assert copied
    assert (tmp_path / "visitsg-essentials").is_dir()


def test_robots_403_fails_open():
    from src.crawl.robots import RobotsCache

    client = MagicMock()
    client.get.return_value = httpx.Response(
        403, text="Forbidden", request=httpx.Request("GET", "https://en.wikivoyage.org/robots.txt")
    )
    cache = RobotsCache(user_agent="test-bot")
    assert cache.allowed("https://en.wikivoyage.org/wiki/Singapore", client=client)


def test_crawl_force_manual_installs_dumps(tmp_path: Path):
    sources, meta = load_and_validate_sources(ROOT / "data" / "sources.yaml")
    results = crawl_all(
        sources,
        meta=meta,
        raw_dir=tmp_path / "raw",
        manual_dir=ROOT / "data" / "manual",
        force_manual=True,
    )
    assert len(results) == len(sources)
    assert all(r.ok for r in results)
    docs = normalize_all_raw(sources, raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed")
    assert len(docs) >= 4
    report = evaluate_topic_buckets(
        sources,
        matrix_path=ROOT / "data" / "coverage_matrix.yaml",
        processed_dir=tmp_path / "processed",
        raw_dir=tmp_path / "raw",
        green_min=400,
        yellow_min=100,
    )
    required = [b for b in report.buckets if b.required]
    assert all(b.status in {"green", "yellow"} for b in required)
    gate = evaluate_phase2_gate(
        sources,
        matrix_path=ROOT / "data" / "coverage_matrix.yaml",
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        manual_dir=ROOT / "data" / "manual",
    )
    assert not gate.sources_missing_content


def test_crawl_falls_back_to_manual_on_robots_block(tmp_path: Path):
    source = _sample_source(
        id="visitsg-essentials",
        license="All rights reserved — fair educational excerpt only",
        seed_urls=("https://www.visitsingapore.com/blocked",),
        allowlist_hosts=("www.visitsingapore.com", "visitsingapore.com"),
        citation=Citation(
            title="Visit Singapore — Plan Your Trip / Travellers Essentials",
            url="https://www.visitsingapore.com/mice/en/tools-and-resources/plan-your-trip/",
        ),
    )
    client = MagicMock()
    fetcher = SeedFetcher(
        user_agent="test-bot",
        delay_seconds=0,
        respect_robots=True,
        client=client,
    )
    fetcher.robots.allowed = MagicMock(return_value=False)  # type: ignore[method-assign]
    result = crawl_source(
        source,
        fetcher=fetcher,
        raw_dir=tmp_path / "raw",
        manual_dir=ROOT / "data" / "manual",
        use_manual_fallback=True,
    )
    assert result.ok
    assert result.manual_copied
    assert any(s.fetch_mode == "manual" for s in result.seeds)


def test_fetch_seed_saves_excerpt_for_arr():
    source = _sample_source(
        license="All rights reserved — fair educational excerpt only",
        seed_urls=("https://example.com/page",),
    )
    html = (
        "<html><head><title>Official Page</title></head>"
        "<body><p>Travel tips for visitors.</p></body></html>"
    )
    response = httpx.Response(
        200, text=html, request=httpx.Request("GET", "https://example.com/page")
    )
    client = MagicMock()
    client.get.return_value = response
    fetcher = SeedFetcher(
        user_agent="test",
        delay_seconds=0,
        respect_robots=False,
        client=client,
    )
    outcome = fetcher.fetch_seed(source, "https://example.com/page")
    assert outcome.ok
    assert outcome.used_excerpt
    assert outcome.extension == ".md"
    assert "Travel tips" in outcome.body


def test_update_matrix_statuses_writes_file(tmp_path: Path):
    sources, _ = load_and_validate_sources(ROOT / "data" / "sources.yaml")
    crawl_all(
        sources,
        raw_dir=tmp_path / "raw",
        manual_dir=ROOT / "data" / "manual",
        force_manual=True,
    )
    normalize_all_raw(sources, raw_dir=tmp_path / "raw", processed_dir=tmp_path / "processed")
    matrix_copy = tmp_path / "coverage_matrix.yaml"
    matrix_copy.write_text(
        (ROOT / "data" / "coverage_matrix.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    report = evaluate_topic_buckets(
        sources,
        matrix_path=matrix_copy,
        processed_dir=tmp_path / "processed",
        green_min=200,
        yellow_min=50,
    )
    update_matrix_statuses(report, matrix_path=matrix_copy)
    text = matrix_copy.read_text(encoding="utf-8")
    assert "phase_2_exit" in text
    assert "status: green" in text or "status: yellow" in text


def test_crawl_script_force_manual_writes_raw(tmp_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("crawl_script", ROOT / "scripts" / "crawl.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    code = mod.main(
        [
            "--force-manual",
            "--raw",
            str(tmp_path / "raw"),
            "--processed",
            str(tmp_path / "processed"),
            "--manual",
            str(ROOT / "data" / "manual"),
            "--matrix",
            str(ROOT / "data" / "coverage_matrix.yaml"),
            "--sources",
            str(ROOT / "data" / "sources.yaml"),
        ]
    )
    assert code in {0, 1}
    assert any((tmp_path / "raw").iterdir())
