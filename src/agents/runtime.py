"""Build HybridRetriever wired to Phase 1.5/4 stores (same path as load)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.graph.store import InMemoryGraphStore, open_graph_store
from src.llm.factory import get_embeddings
from src.ontology.gate import load_entities_file
from src.rag.chroma_store import load_chroma
from src.rag.retrieve import HybridRetriever

REPO_ROOT = Path(__file__).resolve().parents[2]


def build_retriever(
    *,
    embedding_provider: str | None = None,
    chroma_dir: Path | str | None = None,
    entities_path: Path | str | None = None,
    force_memory_graph: bool = False,
) -> HybridRetriever:
    """Open Chroma (+ optional Neo4j/memory graph) for agents."""
    load_dotenv()
    embeddings = get_embeddings(embedding_provider)
    persist = Path(chroma_dir or os.getenv("CHROMA_PATH") or REPO_ROOT / "data" / "chroma")
    store = load_chroma(embeddings=embeddings, persist_dir=persist)

    graph: Any
    if force_memory_graph:
        graph = InMemoryGraphStore()
        ent_path = Path(entities_path or REPO_ROOT / "ontology" / "entities.json")
        if ent_path.is_file():
            entities = load_entities_file(ent_path)
            graph.load_entities(entities, reset=True)
    else:
        graph = open_graph_store(force_memory=False)
        # If we fell back to empty memory, seed from ontology file
        if isinstance(graph, InMemoryGraphStore):
            ent_path = Path(entities_path or REPO_ROOT / "ontology" / "entities.json")
            if ent_path.is_file() and graph.stats().entity_count == 0:
                entities = load_entities_file(ent_path)
                graph.load_entities(entities, reset=True)

    return HybridRetriever(store, graph)
