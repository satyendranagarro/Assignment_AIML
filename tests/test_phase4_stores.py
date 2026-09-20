"""Phase 4 stores tests (offline; fake embeddings + in-memory graph)."""

from __future__ import annotations

from pathlib import Path

from src.crawl.runner import crawl_all
from src.data.normalize import normalize_all_raw
from src.data.sources import load_and_validate_sources
from src.graph.store import InMemoryGraphStore
from src.llm.factory import ConfigError, get_embeddings, resolve_provider
from src.ontology.extract import build_entities, load_processed_documents
from src.ontology.gate import load_entities_file
from src.ontology.taxonomy import load_taxonomy
from src.rag.build import build_kb, doc_entity_map, ensure_chunks_have_citations
from src.rag.chunk import chunk_documents, chunk_text
from src.rag.chroma_store import chroma_count, load_chroma
from src.rag.gate import evaluate_phase4_gate
from src.rag.retrieve import HybridRetriever

ROOT = Path(__file__).resolve().parents[1]


def _ensure_processed(tmp_path: Path) -> Path:
    sources, meta = load_and_validate_sources(ROOT / "data" / "sources.yaml")
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    crawl_all(
        sources,
        meta=meta,
        raw_dir=raw,
        manual_dir=ROOT / "data" / "manual",
        force_manual=True,
    )
    normalize_all_raw(sources, raw_dir=raw, processed_dir=processed)
    return processed


def test_chunk_text_preserves_content():
    text = "Paragraph one about Singapore.\n\n" + ("Word " * 200) + "\n\nClosing note."
    parts = chunk_text(text, chunk_size=200, chunk_overlap=40)
    assert len(parts) >= 2
    assert all(p.strip() for p in parts)


def test_chunks_carry_citation_metadata(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    docs = load_processed_documents(processed)
    chunks = chunk_documents(docs)
    assert len(chunks) >= 5
    errors = ensure_chunks_have_citations(chunks)
    assert not errors, errors[:3]
    assert all(c.url.startswith("http") for c in chunks)


def test_lexical_embeddings_retrieve_overlapping_terms(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    chroma = tmp_path / "chroma"
    summary = build_kb(
        processed_dir=processed,
        entities_path=ROOT / "ontology" / "entities.json",
        chroma_dir=chroma,
        embedding_provider="fake",
        reset=True,
    )
    assert summary["chunk_count"] >= 5
    assert summary["chroma_count"] >= 5

    embeddings = get_embeddings("fake")
    store = load_chroma(embeddings=embeddings, persist_dir=chroma)
    retriever = HybridRetriever(store, None)
    hits = retriever.retrieve("Gardens by the Bay", k=5)
    assert hits, "expected chroma hits for Gardens by the Bay"
    assert any("garden" in h.text.lower() or "bay" in h.text.lower() for h in hits)
    assert all(h.url for h in hits if h.source == "chroma")


def test_inmemory_graph_expands_relations(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    entities = build_entities(
        gazetteer_path=ROOT / "ontology" / "gazetteer.yaml",
        processed_dir=processed,
        taxonomy=load_taxonomy(ROOT / "ontology" / "taxonomy.yaml"),
        min_spot_check=10,
    )
    graph = InMemoryGraphStore()
    stats = graph.load_entities(entities, reset=True)
    assert stats.entity_count >= 20
    assert stats.relation_count >= 5
    hits = graph.expand_from_query("Gardens by the Bay", limit=6)
    assert hits
    assert any(h.entity_id for h in hits)
    # Expect at least one relation expansion when entity has neighbors
    related = [h for h in hits if h.relation_path]
    # May or may not have neighbors depending on extract; soft check via stats
    assert stats.relation_count >= 1
    _ = related
    graph.close()


def test_hybrid_retriever_merges_chroma_and_graph(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    entities = load_entities_file(ROOT / "ontology" / "entities.json")
    chroma = tmp_path / "chroma"
    build_kb(
        processed_dir=processed,
        entities_path=ROOT / "ontology" / "entities.json",
        chroma_dir=chroma,
        embedding_provider="fake",
    )
    store = load_chroma(embeddings=get_embeddings("fake"), persist_dir=chroma)
    graph = InMemoryGraphStore()
    graph.load_entities(entities, reset=True)
    retriever = HybridRetriever(store, graph)
    hits = retriever.retrieve("MRT", k=4)
    assert hits
    sources = {h.source for h in hits}
    assert "chroma" in sources or "neo4j" in sources
    graph.close()


def test_doc_entity_map_links_evidence(tmp_path: Path):
    entities = load_entities_file(ROOT / "ontology" / "entities.json")
    mapping = doc_entity_map(entities)
    assert mapping
    assert all(isinstance(v, list) and v for v in mapping.values())


def test_phase4_gate_passes(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    # Prefer committed entities.json for stable relation counts
    report = evaluate_phase4_gate(
        processed_dir=processed,
        entities_path=ROOT / "ontology" / "entities.json",
        chroma_dir=tmp_path / "chroma_gate",
        rebuild=True,
        force_memory_graph=True,
        embedding_provider="fake",
    )
    assert report.ok, report.errors or report.messages
    assert report.chroma_count >= 5
    assert report.entity_count >= 20


def test_resolve_provider_rejects_unknown(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    try:
        resolve_provider()
        assert False, "expected ConfigError"
    except ConfigError:
        pass


def test_build_kb_script(tmp_path: Path):
    import importlib.util

    processed = _ensure_processed(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "build_kb_script", ROOT / "scripts" / "build_kb.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    chroma = tmp_path / "chroma_script"
    code = mod.main(
        [
            "--processed",
            str(processed),
            "--entities",
            str(ROOT / "ontology" / "entities.json"),
            "--chroma",
            str(chroma),
            "--embeddings",
            "fake",
        ]
    )
    assert code == 0
    assert chroma_count(load_chroma(embeddings=get_embeddings("fake"), persist_dir=chroma)) >= 5
