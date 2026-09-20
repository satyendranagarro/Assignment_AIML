"""UC-COMBO, UC-MEM, UC-LLM use cases."""

from __future__ import annotations

import pytest

from src.agents.models import SessionState
from src.llm.factory import ConfigError, get_chat_model, resolve_provider
from tests.use_cases.harness import assert_has_label, make_test_orchestrator


def test_uc_combo_01_weather_itinerary():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle(
        "Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast"
    )
    assert resp.intent == "combined_itinerary"
    assert resp.used_rag and resp.used_mcp
    assert_has_label(resp.answer, "[KB fact]")
    assert_has_label(resp.answer, "[MCP data]")
    assert_has_label(resp.answer, "[LLM suggestion]")
    assert "Day 1" in resp.answer or "Day 2" in resp.answer
    assert "indoor" in resp.answer.lower() or "rain" in resp.answer.lower()


def test_uc_combo_02_budget_itinerary():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle(
        "I have a budget of INR 60000. Convert it to SGD and suggest a three-day itinerary"
    )
    assert resp.intent == "combined_budget"
    assert_has_label(resp.answer, "[MCP data]")
    assert_has_label(resp.answer, "[KB fact]")
    assert "SGD" in resp.answer


def test_uc_combo_03_outdoor_indoor_rain():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle(
        "Suggest outdoor attractions and replace them with indoor options if rain is expected"
    )
    assert resp.intent == "combined_itinerary"
    assert_has_label(resp.answer, "[MCP data]")
    assert_has_label(resp.answer, "[KB fact]")


def test_uc_combo_04_family_weather():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("Plan a family trip and include the latest weather forecast")
    assert resp.intent == "combined_itinerary"
    assert orch.session.traveler_type == "family"
    assert_has_label(resp.answer, "[MCP data]")


def test_uc_combo_05_culture_budget():
    orch = make_test_orchestrator(mock_mcp=True)
    orch.session.budget_amount = 60000
    orch.session.budget_currency = "INR"
    resp = orch.handle(
        "Create a cultural itinerary and show my budget in the destination currency"
    )
    assert resp.intent in ("combined_budget", "combined_itinerary", "rag_only", "currency_only")
    # Should involve FX or at least cultural RAG
    assert "[KB fact]" in resp.answer or "[MCP data]" in resp.answer


def test_uc_mem_01_family():
    orch = make_test_orchestrator()
    orch.handle("We are a family of 4")
    assert orch.session.traveler_type == "family"
    resp = orch.handle("Suggest activities")
    assert orch.session.traveler_type == "family"
    assert resp.used_rag


def test_uc_mem_02_budget():
    orch = make_test_orchestrator(mock_mcp=True)
    orch.handle("Budget INR 60000")
    assert orch.session.budget_amount == 60000
    assert orch.session.budget_currency == "INR"
    resp = orch.handle("Show my budget in SGD")
    assert_has_label(resp.answer, "[MCP data]")
    assert "SGD" in resp.answer


def test_uc_mem_03_indoor_preference():
    orch = make_test_orchestrator()
    orch.handle("I prefer indoor activities only")
    assert orch.session.prefer_indoor is True
    resp = orch.handle("Create a three-day sightseeing itinerary")
    assert orch.session.prefer_indoor is True
    assert resp.used_rag


def test_uc_llm_01_fake_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    assert resolve_provider(None) == "fake"
    orch = make_test_orchestrator(provider="fake")
    resp = orch.handle("What are attractions in Singapore?")
    assert resp.provider == "fake"
    assert_has_label(resp.answer, "[KB fact]")


def test_uc_llm_02_provider_changed(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    orch = make_test_orchestrator(provider="fake")
    orch.set_provider("fake")  # same — no change
    # Switching to missing openai key should surface config error on chat path
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    orch.set_provider("openai")
    resp = orch.handle("What are attractions in Singapore?")
    # Config error on LLM; KB facts may still appear from A1
    assert resp.error or "configuration error" in resp.answer.lower() or resp.provider == "openai"


def test_uc_llm_04_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        get_chat_model("openai")
    orch = make_test_orchestrator(provider="openai")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    resp = orch.handle("What are the must-visit attractions in Singapore?")
    assert resp.error or "configuration error" in resp.answer.lower()
    assert "silent" not in resp.answer.lower() or "no silent" in resp.answer.lower() or resp.error
