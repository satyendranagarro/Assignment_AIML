"""Retrieval hit models + vector / hybrid retrievers."""

from __future__ import annotations

import time
from typing import Any

from src.observability import log_event
from src.rag.models import RetrievalHit


def retrieve_chroma(
    store: Any,
    query: str,
    *,
    k: int = 5,
) -> list[RetrievalHit]:
    t0 = time.perf_counter()
    # Prefer distance scores; normalize to a [0,1]-ish relevance without Chroma warnings
    try:
        pairs = store.similarity_search_with_score(query, k=k)
        hits: list[RetrievalHit] = []
        for doc, distance in pairs:
            meta = dict(doc.metadata or {})
            # Chroma L2 / cosine distance → crude relevance in (0, 1]
            dist = float(distance)
            score = 1.0 / (1.0 + max(dist, 0.0))
            hits.append(
                RetrievalHit(
                    text=doc.page_content,
                    score=score,
                    source="chroma",
                    title=str(meta.get("title", "")),
                    url=str(meta.get("url", "")),
                    doc_id=str(meta.get("doc_id", "")),
                    source_id=str(meta.get("source_id", "")),
                    chunk_id=str(meta.get("chunk_id", "")),
                    metadata=meta,
                )
            )
    except Exception:
        docs = store.similarity_search(query, k=k)
        hits = []
        for i, doc in enumerate(docs):
            meta = dict(doc.metadata or {})
            hits.append(
                RetrievalHit(
                    text=doc.page_content,
                    score=1.0 - (i * 0.05),
                    source="chroma",
                    title=str(meta.get("title", "")),
                    url=str(meta.get("url", "")),
                    doc_id=str(meta.get("doc_id", "")),
                    source_id=str(meta.get("source_id", "")),
                    chunk_id=str(meta.get("chunk_id", "")),
                    metadata=meta,
                )
            )
    log_event(
        "retrieve.end",
        "Chroma similarity search",
        store="chroma",
        query_preview=query,
        hit_count=len(hits),
        latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        status="ok",
    )
    return hits


class HybridRetriever:
    """Chroma primary + Neo4j / in-memory graph expansion (GraphRAG)."""

    def __init__(
        self,
        chroma_store: Any,
        graph: Any | None = None,
        *,
        chroma_k: int = 5,
        graph_limit: int = 8,
    ) -> None:
        self.chroma = chroma_store
        self.graph = graph
        self.chroma_k = chroma_k
        self.graph_limit = graph_limit

    def retrieve(self, query: str, *, k: int | None = None) -> list[RetrievalHit]:
        t0 = time.perf_counter()
        log_event("retrieve.start", "Hybrid retrieve", query_preview=query, store="hybrid")
        chroma_hits = retrieve_chroma(self.chroma, query, k=k or self.chroma_k)
        graph_hits: list[RetrievalHit] = []
        if self.graph is not None:
            try:
                graph_hits = self.graph.expand_from_query(
                    query, seed_hits=chroma_hits, limit=self.graph_limit
                )
            except Exception as exc:  # noqa: BLE001 — surface as empty expand
                log_event(
                    "retrieve.error",
                    "Graph expand failed",
                    store="neo4j",
                    status="error",
                    error=str(exc)[:200],
                )

        merged = _merge_hits(chroma_hits, graph_hits)
        log_event(
            "retrieve.end",
            "Hybrid retrieve done",
            store="hybrid",
            query_preview=query,
            hit_count=len(merged),
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            status="ok",
        )
        return merged


def _merge_hits(*groups: list[RetrievalHit]) -> list[RetrievalHit]:
    seen: set[str] = set()
    out: list[RetrievalHit] = []
    for group in groups:
        for hit in group:
            key = hit.chunk_id or hit.entity_id or f"{hit.source}:{hit.url}:{hit.text[:40]}"
            if key in seen:
                continue
            seen.add(key)
            out.append(hit)
    return out
