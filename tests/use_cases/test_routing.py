"""UC-ROUTE — intent classification."""

from __future__ import annotations

import pytest

from src.agents.router import classify_intent
from tests.use_cases.harness import make_test_orchestrator


@pytest.mark.parametrize(
    "query,intent",
    [
        ("What are the must-visit attractions in Singapore?", "rag_only"),
        ("What is the weather in Singapore?", "weather_only"),
        ("Convert INR 50000 to SGD", "currency_only"),
        (
            "Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast",
            "combined_itinerary",
        ),
        ("Book me a hotel in Marina Bay", "out_of_scope"),
    ],
)
def test_uc_route_classify(query: str, intent: str):
    assert classify_intent(query) == intent


def test_uc_route_01_rag_no_mcp():
    orch = make_test_orchestrator()
    resp = orch.handle("What are the must-visit attractions in Singapore?")
    assert resp.intent == "rag_only"
    assert resp.used_mcp is False
    assert resp.used_rag is True


def test_uc_route_02_weather():
    orch = make_test_orchestrator()
    resp = orch.handle("What is the weather in Singapore?")
    assert resp.intent == "weather_only"
    assert resp.used_mcp is True


def test_uc_route_03_currency():
    orch = make_test_orchestrator()
    resp = orch.handle("Convert INR 50000 to SGD")
    assert resp.intent == "currency_only"
    assert resp.used_mcp is True


def test_uc_route_04_combo():
    orch = make_test_orchestrator()
    resp = orch.handle(
        "Create a three-day Singapore itinerary for next week and adjust according to the weather forecast"
    )
    assert resp.intent == "combined_itinerary"
    assert resp.used_rag and resp.used_mcp


def test_uc_route_05_out_of_scope():
    orch = make_test_orchestrator()
    resp = orch.handle("Book me a hotel")
    assert resp.intent == "out_of_scope"
    assert "out of scope" in resp.answer.lower()


def test_uc_neg_04_temples_to_rag():
    assert classify_intent("What are the best temples in Chinatown?") == "rag_only"
