"""MCP weather client — in-process tools, mock mode, or forced failure."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from mcp_servers.weather import mock as weather_mock
from mcp_servers.weather.tools import (
    WeatherToolError,
    fetch_current_weather,
    fetch_forecast,
    format_current,
    format_forecast,
)


class WeatherMCPError(RuntimeError):
    """Weather MCP unavailable or failed (never fabricate temps)."""


def _mock_mode() -> bool:
    load_dotenv()
    return (os.getenv("MCP_MOCK_MODE") or "").strip().lower() in {"1", "true", "yes"}


class WeatherClient:
    """Thin client used by A2/A4. Prefer live Open-Meteo; optional mock for demos."""

    def __init__(
        self,
        *,
        mock: bool | None = None,
        force_fail: bool = False,
    ) -> None:
        self.mock = _mock_mode() if mock is None else mock
        self.force_fail = force_fail

    def current(self, *, place: str = "Singapore") -> dict[str, Any]:
        if self.force_fail:
            raise WeatherMCPError("Weather MCP unavailable (forced failure)")
        try:
            if self.mock:
                return weather_mock.mock_current(place=place)
            return fetch_current_weather(place=place)
        except WeatherToolError as exc:
            if self.mock:
                return weather_mock.mock_current(place=place)
            raise WeatherMCPError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise WeatherMCPError(f"Weather MCP error: {exc}") from exc

    def forecast(self, *, days: int = 3, place: str = "Singapore") -> dict[str, Any]:
        if self.force_fail:
            raise WeatherMCPError("Weather MCP unavailable (forced failure)")
        try:
            if self.mock:
                return weather_mock.mock_forecast(days=days, place=place)
            return fetch_forecast(days=days, place=place)
        except WeatherToolError as exc:
            raise WeatherMCPError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise WeatherMCPError(f"Weather MCP error: {exc}") from exc

    def format_current(self, payload: dict[str, Any]) -> str:
        return format_current(payload)

    def format_forecast(self, payload: dict[str, Any]) -> str:
        return format_forecast(payload)
