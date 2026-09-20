"""Currency conversion — Frankfurter (ECB) API, no key required."""

from __future__ import annotations

from typing import Any

import httpx

FRANKFURTER = "https://api.frankfurter.dev/v1/latest"


class CurrencyToolError(RuntimeError):
    """Upstream FX API failure or invalid response."""


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    src = from_currency.strip().upper()
    dst = to_currency.strip().upper()
    if src == dst:
        return {
            "amount": float(amount),
            "from_currency": src,
            "to_currency": dst,
            "rate": 1.0,
            "converted": float(amount),
            "source": "identity",
            "label": "MCP data",
        }
    params = {"amount": amount, "from": src, "to": dst}
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(FRANKFURTER, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise CurrencyToolError(f"Currency API request failed: {exc}") from exc

    rates = data.get("rates") or {}
    if dst not in rates:
        raise CurrencyToolError(f"No rate for {src}→{dst} in API response")
    converted = float(rates[dst])
    rate = converted / float(amount) if float(amount) else float(rates[dst])
    return {
        "amount": float(amount),
        "from_currency": src,
        "to_currency": dst,
        "rate": rate,
        "converted": converted,
        "date": data.get("date"),
        "source": "frankfurter",
        "label": "MCP data",
    }


def format_conversion(payload: dict[str, Any]) -> str:
    return (
        f"{payload.get('amount')} {payload.get('from_currency')} = "
        f"{payload.get('converted')} {payload.get('to_currency')} "
        f"(rate {payload.get('rate')}; source {payload.get('source')}"
        f"{', date ' + str(payload['date']) if payload.get('date') else ''})."
    )
