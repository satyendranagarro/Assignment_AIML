"""UC-RAG use cases (offline fake LLM + fake store)."""

from __future__ import annotations

from tests.use_cases.harness import assert_has_label, make_test_orchestrator


def test_uc_rag_01_attractions():
    orch = make_test_orchestrator()
    resp = orch.handle("What are the must-visit attractions in Singapore?")
    assert resp.intent == "rag_only"
    assert resp.used_mcp is False
    assert_has_label(resp.answer, "[KB fact]")
    assert resp.citations or "http" in resp.answer


def test_uc_rag_02_neighbourhoods():
    orch = make_test_orchestrator()
    resp = orch.handle("Which neighbourhoods are suitable for cultural experiences?")
    assert resp.intent == "rag_only"
    assert_has_label(resp.answer, "[KB fact]")
    assert "Chinatown" in resp.answer or "cultural" in resp.answer.lower()


def test_uc_rag_03_transport():
    orch = make_test_orchestrator()
    resp = orch.handle("How can a tourist travel around Singapore?")
    assert "MRT" in resp.answer or "bus" in resp.answer.lower()
    assert_has_label(resp.answer, "[KB fact]")


def test_uc_rag_04_family():
    orch = make_test_orchestrator()
    orch.handle("We are a family of 4")
    resp = orch.handle("Suggest activities for a family with children")
    assert orch.session.traveler_type == "family"
    assert_has_label(resp.answer, "[KB fact]")


def test_uc_rag_05_itinerary_labels():
    orch = make_test_orchestrator()
    resp = orch.handle("Create a three-day sightseeing itinerary")
    # Pure itinerary without weather → rag_only; still day-wise via KB excerpts + suggestion
    assert resp.intent == "rag_only"
    assert_has_label(resp.answer, "[KB fact]")
    assert "[LLM suggestion]" in resp.answer or "Day" in resp.answer or "itinerary" in resp.answer.lower()


def test_uc_rag_06_indoor():
    orch = make_test_orchestrator()
    resp = orch.handle("What indoor attractions can I visit?")
    assert "indoor" in resp.answer.lower() or "museum" in resp.answer.lower()
    assert_has_label(resp.answer, "[KB fact]")


def test_uc_rag_07_antarctica_gap():
    orch = make_test_orchestrator()
    resp = orch.handle("What is the best nightlife in Antarctica?")
    assert "not" in resp.answer.lower() or "cannot" in resp.answer.lower() or "do not" in resp.answer.lower()
    assert "invent" in resp.answer.lower() or "knowledge-base" in resp.answer.lower() or "coverage" in resp.answer.lower()


def test_uc_neg_01_empty_retrieval():
    orch = make_test_orchestrator(empty_retriever=True)
    resp = orch.handle("Tell me about secret volcanoes under the CBD")
    assert "not" in resp.answer.lower() or "no" in resp.answer.lower()
    assert_has_label(resp.answer, "[Error]")
