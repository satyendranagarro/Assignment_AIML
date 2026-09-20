"""Documented mock FX payloads for MCP_MOCK_MODE demos (not live rates)."""

from __future__ import annotations

from typing import Any

# Approximate demo rates — clearly labeled mock
_MOCK_RATES: dict[tuple[str, str], float] = {
    ("INR", "SGD"): 0.0155,
    ("SGD", "INR"): 64.5,
    ("USD", "SGD"): 1.35,
    ("SGD", "USD"): 0.74,
    ("USD", "INR"): 83.0,
    ("INR", "USD"): 0.012,
}


def mock_convert(amount: float, from_currency: str, to_currency: str) -> dict[str, Any]:
    src = from_currency.strip().upper()
    dst = to_currency.strip().upper()
    if src == dst:
        rate = 1.0
    else:
        rate = _MOCK_RATES.get((src, dst))
        if rate is None:
            # Try inverse pair
            inv = _MOCK_RATES.get((dst, src))
            if inv is None:
                raise ValueError(f"Mock FX has no rate for {src}→{dst}")
            rate = 1.0 / inv
    converted = float(amount) * rate
    return {
        "amount": float(amount),
        "from_currency": src,
        "to_currency": dst,
        "rate": rate,
        "converted": round(converted, 4),
        "date": "2026-09-20",
        "source": "mcp-mock",
        "label": "MCP data",
        "mock": True,
    }
