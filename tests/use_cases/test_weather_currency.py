"""UC-WX and UC-FX use cases."""

from __future__ import annotations

from tests.use_cases.harness import assert_has_label, make_test_orchestrator


def test_uc_wx_01_current():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("What is the weather in Singapore?")
    assert resp.intent == "weather_only"
    assert_has_label(resp.answer, "[MCP data]")
    assert "°C" in resp.answer or "temperature" in resp.answer.lower() or "Forecast" in resp.answer


def test_uc_wx_02_forecast():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("What is the forecast for the next three days?")
    assert_has_label(resp.answer, "[MCP data]")
    assert "2026-09" in resp.answer or "Day" in resp.answer or "Forecast" in resp.answer


def test_uc_wx_03_rain():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("Is rain expected during my trip?")
    assert_has_label(resp.answer, "[MCP data]")
    assert "rain" in resp.answer.lower()


def test_uc_wx_04_indoor_outdoor():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("Should I plan indoor or outdoor activities tomorrow?")
    assert_has_label(resp.answer, "[MCP data]")
    assert "[LLM suggestion]" in resp.answer


def test_uc_wx_05_mcp_down():
    orch = make_test_orchestrator(weather_fail=True, mock_mcp=False)
    resp = orch.handle("What is the weather in Singapore?")
    assert_has_label(resp.answer, "[Error]")
    assert "fabricat" in resp.answer.lower() or "unavailable" in resp.answer.lower()
    assert "31" not in resp.answer  # no mock temp leaked


def test_uc_neg_02_weather_timeout():
    orch = make_test_orchestrator(weather_fail=True, mock_mcp=False)
    resp = orch.handle("What is the forecast for Singapore?")
    assert resp.error
    assert "fabricat" in resp.answer.lower() or "unavailable" in resp.answer.lower()


def test_uc_fx_01_inr_sgd():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("Convert INR 50000 to SGD")
    assert resp.intent == "currency_only"
    assert_has_label(resp.answer, "[MCP data]")
    assert "SGD" in resp.answer
    assert "rate" in resp.answer.lower() or "INR" in resp.answer


def test_uc_fx_02_reverse():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("How much is 200 SGD in INR?")
    assert "INR" in resp.answer
    assert_has_label(resp.answer, "[MCP data]")


def test_uc_fx_03_missing_amount_or_state():
    orch = make_test_orchestrator(mock_mcp=True)
    resp = orch.handle("Convert my travel budget from USD to Singapore dollars")
    # No amount in session → ask
    assert "amount" in resp.answer.lower() or "provide" in resp.answer.lower()


def test_uc_fx_04_mcp_down():
    orch = make_test_orchestrator(currency_fail=True, mock_mcp=False)
    resp = orch.handle("Convert INR 1000 to SGD")
    assert_has_label(resp.answer, "[Error]")
    assert "fabricat" in resp.answer.lower() or "unavailable" in resp.answer.lower()


def test_uc_neg_03_currency_500():
    orch = make_test_orchestrator(currency_fail=True, mock_mcp=False)
    resp = orch.handle("Convert USD 100 to SGD")
    assert resp.error
    assert "rate" in resp.answer.lower() or "unavailable" in resp.answer.lower()
