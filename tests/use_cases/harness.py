"""Phase 5 agent unit tests + use-case harness helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.models import SessionState
from src.agents.orchestrator import OrchestratorAgent
from src.rag.models import RetrievalHit
from src.rag.retrieve import HybridRetriever
from mcp_servers.weather.client import WeatherClient
from mcp_servers.currency.client import CurrencyClient


@dataclass
class FakeStore:
    """Minimal Chroma stand-in with similarity_search_with_score."""

    docs: list[tuple[str, dict[str, Any], float]] = field(default_factory=list)

    def similarity_search_with_score(self, query: str, k: int = 5):
        from langchain_core.documents import Document

        q = query.lower()
        scored = []
        for text, meta, base in self.docs:
            overlap = sum(1 for t in q.split() if t in text.lower())
            score_dist = max(0.01, 1.0 - 0.1 * overlap - base)
            scored.append((Document(page_content=text, metadata=meta), score_dist))
        scored.sort(key=lambda x: x[1])
        return scored[:k]

    def similarity_search(self, query: str, k: int = 5):
        return [d for d, _ in self.similarity_search_with_score(query, k=k)]


def sample_hits_store() -> FakeStore:
    return FakeStore(
        docs=[
            (
                "Gardens by the Bay is a major outdoor attraction with conservatories that are indoor.",
                {
                    "title": "Wikivoyage Singapore",
                    "url": "https://en.wikivoyage.org/wiki/Singapore",
                    "doc_id": "d1",
                    "source_id": "wikivoyage",
                    "chunk_id": "c1",
                },
                0.2,
            ),
            (
                "Chinatown offers cultural experiences, temples, and heritage streets for visitors.",
                {
                    "title": "Visit Singapore Things to Do",
                    "url": "https://www.visitsingapore.com/things-to-do/",
                    "doc_id": "d2",
                    "source_id": "vs-ttd",
                    "chunk_id": "c2",
                },
                0.15,
            ),
            (
                "Tourists travel around Singapore using MRT, buses, and taxis. EZ-Link cards help.",
                {
                    "title": "Essential Travel Information",
                    "url": "https://www.visitsingapore.com/travel-guide-tips/getting-around/",
                    "doc_id": "d3",
                    "source_id": "vs-essential",
                    "chunk_id": "c3",
                },
                0.1,
            ),
            (
                "Family-friendly indoor options include museums and aquariums suitable for children.",
                {
                    "title": "Family activities",
                    "url": "https://www.visitsingapore.com/editorials/family/",
                    "doc_id": "d4",
                    "source_id": "vs-family",
                    "chunk_id": "c4",
                },
                0.1,
            ),
            (
                "National Gallery and shopping malls are popular indoor attractions when it rains.",
                {
                    "title": "Indoor attractions",
                    "url": "https://www.visitsingapore.com/indoor/",
                    "doc_id": "d5",
                    "source_id": "vs-indoor",
                    "chunk_id": "c5",
                },
                0.1,
            ),
            (
                "Three-day sample itineraries cover Marina Bay, heritage districts, and Sentosa.",
                {
                    "title": "Sample Itineraries",
                    "url": "https://www.visitsingapore.com/itineraries/",
                    "doc_id": "d6",
                    "source_id": "vs-itin",
                    "chunk_id": "c6",
                },
                0.1,
            ),
        ]
    )


def make_test_orchestrator(
    *,
    provider: str = "fake",
    weather_fail: bool = False,
    currency_fail: bool = False,
    mock_mcp: bool = True,
    empty_retriever: bool = False,
    session: SessionState | None = None,
) -> OrchestratorAgent:
    store = FakeStore(docs=[]) if empty_retriever else sample_hits_store()
    retriever = HybridRetriever(store, None)
    return OrchestratorAgent(
        retriever,
        weather=WeatherClient(mock=mock_mcp, force_fail=weather_fail),
        currency=CurrencyClient(mock=mock_mcp, force_fail=currency_fail),
        provider=provider,
        session=session or SessionState(session_id="test"),
    )


def assert_has_label(answer: str, label: str) -> None:
    assert label in answer, f"expected {label!r} in answer:\n{answer}"
