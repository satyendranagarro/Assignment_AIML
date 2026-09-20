"""Phase 1 gate + normalize unit tests (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from src.data.coverage import evaluate_phase1_gate
from src.data.models import Citation, Source
from src.data.normalize import normalize_raw_payload, write_normalized_document
from src.data.sources import load_and_validate_sources, validate_sources

ROOT = Path(__file__).resolve().parents[1]


def test_sources_registry_loads_at_least_three():
    sources, meta = load_and_validate_sources(ROOT / "data" / "sources.yaml")
    assert meta["destination"] == "Singapore"
    assert len(sources) >= 3
    for src in sources:
        assert src.citation.title
        assert src.citation.url.startswith("http")
    wiki = next(s for s in sources if s.id == "wikivoyage-singapore")
    assert "/wiki/Singapore" in wiki.url_path_prefixes
    assert "Singapore" in wiki.url_path_contains


def test_phase1_gate_passes():
    report = evaluate_phase1_gate(
        sources_path=ROOT / "data" / "sources.yaml",
        matrix_path=ROOT / "data" / "coverage_matrix.yaml",
    )
    assert report.ok, report.messages
    assert report.source_count >= 3
    assert report.required_topics >= 1
    assert not report.unmapped_required
    assert not report.unknown_source_refs


def test_validate_sources_rejects_missing_citation():
    bad = Source(
        id="bad",
        title="Bad",
        url="https://example.com",
        publisher="x",
        license="x",
        reuse_notes="",
        fetch_mode="crawl",
        priority=1,
        topics=("attractions",),
        seed_urls=("https://example.com",),
        allowlist_hosts=("example.com",),
        citation=Citation(title="", url=""),
    )
    errors = validate_sources([bad, bad], min_count=3)
    assert errors


def test_normalize_preserves_citation(tmp_path: Path):
    source = Source(
        id="wikivoyage-singapore",
        title="Singapore – Travel guide at Wikivoyage",
        url="https://en.wikivoyage.org/wiki/Singapore",
        publisher="Wikivoyage",
        license="CC BY-SA 4.0",
        reuse_notes="",
        fetch_mode="crawl",
        priority=1,
        topics=("attractions", "transport"),
        seed_urls=("https://en.wikivoyage.org/wiki/Singapore",),
        allowlist_hosts=("en.wikivoyage.org",),
        citation=Citation(
            title="Singapore – Travel guide at Wikivoyage",
            url="https://en.wikivoyage.org/wiki/Singapore",
        ),
    )
    html = """
    <html><head><title>Ignore</title></head>
    <body><h1>Districts</h1><p>Chinatown and Little India are cultural precincts.</p>
    <script>evil()</script></body></html>
    """
    doc = normalize_raw_payload(source=source, html=html)
    assert "Chinatown" in doc.text
    assert "evil" not in doc.text
    assert doc.title == source.citation.title
    assert doc.url == source.citation.url
    assert doc.citation_metadata()["title"] == source.citation.title

    out = write_normalized_document(doc, processed_dir=tmp_path)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["url"] == source.citation.url
    assert loaded["source_id"] == source.id


def test_ingest_script_exit_zero():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ingest_script", ROOT / "scripts" / "ingest.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    code = mod.main(["--sources", str(ROOT / "data" / "sources.yaml")])
    assert code == 0
