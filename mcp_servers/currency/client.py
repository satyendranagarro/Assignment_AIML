"""MCP currency client — in-process Frankfurter, mock mode, or forced failure."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from mcp_servers.currency import mock as currency_mock
from mcp_servers.currency.tools import (
    CurrencyToolError,
    convert_currency,
    format_conversion,
)


class CurrencyMCPError(RuntimeError):
    """Currency MCP unavailable or failed (never fabricate rates)."""


def _mock_mode() -> bool:
    load_dotenv()
    return (os.getenv("MCP_MOCK_MODE") or "").strip().lower() in {"1", "true", "yes"}


class CurrencyClient:
    def __init__(
        self,
        *,
        mock: bool | None = None,
        force_fail: bool = False,
    ) -> None:
        self.mock = _mock_mode() if mock is None else mock
        self.force_fail = force_fail

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> dict[str, Any]:
        if self.force_fail:
            raise CurrencyMCPError("Currency MCP unavailable (forced failure)")
        try:
            if self.mock:
                return currency_mock.mock_convert(amount, from_currency, to_currency)
            return convert_currency(amount, from_currency, to_currency)
        except (CurrencyToolError, ValueError) as exc:
            raise CurrencyMCPError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise CurrencyMCPError(f"Currency MCP error: {exc}") from exc

    def format(self, payload: dict[str, Any]) -> str:
        return format_conversion(payload)
