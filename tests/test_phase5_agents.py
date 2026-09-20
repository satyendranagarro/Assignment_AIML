"""Phase 5 smoke: router, response labels, MCP clients (mock), orchestrator."""

from __future__ import annotations

from src.agents.router import classify_intent
from src.agents.models import LabeledBlock, render_blocks
from tests.use_cases.harness import make_test_orchestrator
from mcp_servers.weather.client import WeatherClient
from mcp_servers.currency.client import CurrencyClient


def test_classify_intents_smoke():
    assert classify_intent("weather please") == "weather_only"
    assert classify_intent("convert INR to SGD") == "currency_only"


def test_labeled_block_render():
    text = render_blocks(
        [
            LabeledBlock(kind="kb_fact", text="Fact", citations=[{"title": "T", "url": "http://x"}]),
            LabeledBlock(kind="mcp_data", text="Wx"),
        ]
    )
    assert "[KB fact]" in text and "[MCP data]" in text
    assert "http://x" in text


def test_mock_weather_and_currency():
    wx = WeatherClient(mock=True)
    cur = CurrencyClient(mock=True)
    assert wx.current()["mock"] is True
    assert cur.convert(100, "INR", "SGD")["mock"] is True


def test_orchestrator_end_to_end_combo():
    orch = make_test_orchestrator(mock_mcp=True, provider="fake")
    resp = orch.handle(
        "Create a three-day Singapore itinerary and adjust according to the weather forecast"
    )
    assert resp.intent == "combined_itinerary"
    assert "[KB fact]" in resp.answer
    assert "[MCP data]" in resp.answer
