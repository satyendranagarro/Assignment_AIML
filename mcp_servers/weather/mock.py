"""Documented mock weather payloads for MCP_MOCK_MODE demos (not live data)."""

from __future__ import annotations

from typing import Any


def mock_current(*, place: str = "Singapore") -> dict[str, Any]:
    return {
        "place": place,
        "latitude": 1.3521,
        "longitude": 103.8198,
        "observed_at": "2026-09-20T12:00",
        "temperature_c": 31.0,
        "humidity_pct": 75,
        "precipitation_mm": 0.0,
        "weather_code": 1,
        "wind_speed_kmh": 12.0,
        "source": "mcp-mock",
        "label": "MCP data",
        "mock": True,
    }


def mock_forecast(*, days: int = 3, place: str = "Singapore") -> dict[str, Any]:
    days = max(1, min(int(days), 7))
    # Day 0 dry, day 1 rain likely — useful for indoor/outdoor planning demos
    base = [
        {
            "date": "2026-09-21",
            "temp_max_c": 32.0,
            "temp_min_c": 26.0,
            "precipitation_mm": 0.2,
            "precip_probability_pct": 20,
            "weather_code": 1,
            "rain_likely": False,
        },
        {
            "date": "2026-09-22",
            "temp_max_c": 30.0,
            "temp_min_c": 25.0,
            "precipitation_mm": 8.5,
            "precip_probability_pct": 80,
            "weather_code": 61,
            "rain_likely": True,
        },
        {
            "date": "2026-09-23",
            "temp_max_c": 31.0,
            "temp_min_c": 26.0,
            "precipitation_mm": 1.0,
            "precip_probability_pct": 45,
            "weather_code": 3,
            "rain_likely": False,
        },
    ]
    return {
        "place": place,
        "days": base[:days],
        "source": "mcp-mock",
        "label": "MCP data",
        "mock": True,
    }
