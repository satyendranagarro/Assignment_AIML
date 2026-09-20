"""Phase 4 gate: retrieval smoke + graph integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.graph.store import GraphStore, InMemoryGraphStore, open_graph_store
from src.llm.factory import get_embeddings
from src.ontology.gate import load_entities_file
from src.ontology.extract import load_processed_documents
from src.rag.build import DEFAULT_ENTITIES, DEFAULT_PROCESSED, build_kb, doc_entity_map, ensure_chunks_have_citations
from src.rag.chunk import chunk_documents
from src.rag.chroma_store import chroma_count, load_chroma
from src.rag.retrieve import HybridRetriever

REPO_ROOT = Path(__file__).resolve().parents[2]

SMOKE_QUERIES = (
    "Gardens by the Bay",
    "MRT transport",
    "Chinatown food",
)


@dataclass
class Phase4GateReport:
    ok: bool
    chunk_count: int
    chroma_count: int
    entity_count: int
    relation_count: int
    graph_backend: str
    smoke_hits: dict[str, int] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "chunk_count": self.chunk_count,
            "chroma_count": self.chroma_count,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "graph_backend": self.graph_backend,
            "smoke_hits": dict(self.smoke_hits),
            "messages": list(self.messages),
            "errors": list(self.errors),
        }


def evaluate_phase4_gate(
    *,
    processed_dir: Path | str = DEFAULT_PROCESSED,
    entities_path: Path | str = DEFAULT_ENTITIES,
    chroma_dir: Path | str | None = None,
    rebuild: bool = True,
    force_memory_graph: bool = True,
    embedding_provider: str = "fake",
    min_chunks: int = 5,
    min_entities: int = 20,
    min_relations: int = 5,
) -> Phase4GateReport:
    messages: list[str] = []
    errors: list[str] = []
    chroma_path = Path(chroma_dir) if chroma_dir else REPO_ROOT / "data" / ".tmp_phase4_chroma"

    docs = load_processed_documents(processed_dir)
    entities = load_entities_file(entities_path) if Path(entities_path).is_file() else []
    mapping = doc_entity_map(entities)
    chunks = chunk_documents(docs, doc_entity_map=mapping)
    cite_errors = ensure_chunks_have_citations(chunks)
    errors.extend(cite_errors)

    if rebuild or not Path(chroma_path).exists():
        summary = build_kb(
            processed_dir=processed_dir,
            entities_path=entities_path,
            chroma_dir=chroma_path,
            embedding_provider=embedding_provider,
            reset=True,
        )
        chunk_count = int(summary["chunk_count"])
        chroma_n = int(summary["chroma_count"])
    else:
        chunk_count = len(chunks)
        embeddings = get_embeddings(embedding_provider)
        store = load_chroma(embeddings=embeddings, persist_dir=chroma_path)
        chroma_n = chroma_count(store)

    embeddings = get_embeddings(embedding_provider)
    store = load_chroma(embeddings=embeddings, persist_dir=chroma_path)

    graph: GraphStore
    if force_memory_graph:
        graph = InMemoryGraphStore()
    else:
        graph = open_graph_store(prefer_neo4j=True)
    gstats = graph.load_entities(entities, reset=True)

    retriever = HybridRetriever(store, graph)
    smoke_hits: dict[str, int] = {}
    for q in SMOKE_QUERIES:
        hits = retriever.retrieve(q, k=4)
        smoke_hits[q] = len(hits)
        if not hits:
            errors.append(f"smoke miss: no hits for {q!r}")
        else:
            # Prefer at least one chroma hit with citation url for vector queries
            chroma_ok = any(h.source == "chroma" and h.url for h in hits)
            if not chroma_ok and not any(h.source == "neo4j" for h in hits):
                errors.append(f"smoke weak: no cited chroma/graph hit for {q!r}")

    graph.close()

    if chunk_count >= min_chunks:
        messages.append(f"Chunks OK ({chunk_count} ≥ {min_chunks})")
    else:
        errors.append(f"Chunks FAIL ({chunk_count} < {min_chunks})")

    if chroma_n >= min_chunks:
        messages.append(f"Chroma OK ({chroma_n} vectors)")
    else:
        errors.append(f"Chroma FAIL ({chroma_n} < {min_chunks})")

    if gstats.entity_count >= min_entities:
        messages.append(f"Graph entities OK ({gstats.entity_count})")
    else:
        errors.append(f"Graph entities FAIL ({gstats.entity_count} < {min_entities})")

    if gstats.relation_count >= min_relations:
        messages.append(f"Graph relations OK ({gstats.relation_count})")
    else:
        errors.append(f"Graph relations FAIL ({gstats.relation_count} < {min_relations})")

    messages.append(f"Graph backend: {gstats.backend}")
    for q, n in smoke_hits.items():
        messages.append(f"Smoke {q!r}: {n} hits")

    ok = not errors and chunk_count >= min_chunks and chroma_n >= min_chunks
    if ok:
        messages.append(
            "Phase 4 gate PASS — hybrid Chroma + graph expansion ready for Phase 5"
        )
    else:
        messages.append("Phase 4 gate FAIL — fix retrieval/graph before agents")

    return Phase4GateReport(
        ok=ok,
        chunk_count=chunk_count,
        chroma_count=chroma_n,
        entity_count=gstats.entity_count,
        relation_count=gstats.relation_count,
        graph_backend=gstats.backend,
        smoke_hits=smoke_hits,
        messages=messages,
        errors=errors,
    )
