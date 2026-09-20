"""Weather tool logic — Open-Meteo (no API key). Singapore default."""

from __future__ import annotations

from typing import Any

import httpx

# Singapore downtown approx
DEFAULT_LAT = 1.3521
DEFAULT_LON = 103.8198
DEFAULT_PLACE = "Singapore"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


class WeatherToolError(RuntimeError):
    """Upstream weather API failure or invalid response."""


def fetch_current_weather(
    *,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    place: str = DEFAULT_PLACE,
    timeout: float = 15.0,
) -> dict[str, Any]:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,precipitation",
        "timezone": "Asia/Singapore",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(OPEN_METEO, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise WeatherToolError(f"Weather API request failed: {exc}") from exc

    current = data.get("current") or {}
    if not current:
        raise WeatherToolError("Weather API returned no current conditions")
    return {
        "place": place,
        "latitude": latitude,
        "longitude": longitude,
        "observed_at": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "humidity_pct": current.get("relative_humidity_2m"),
        "precipitation_mm": current.get("precipitation"),
        "weather_code": current.get("weather_code"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "source": "open-meteo",
        "label": "MCP data",
    }


def fetch_forecast(
    *,
    days: int = 3,
    latitude: float = DEFAULT_LAT,
    longitude: float = DEFAULT_LON,
    place: str = DEFAULT_PLACE,
    timeout: float = 15.0,
) -> dict[str, Any]:
    days = max(1, min(int(days), 7))
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "forecast_days": days,
        "timezone": "Asia/Singapore",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(OPEN_METEO, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise WeatherToolError(f"Weather forecast request failed: {exc}") from exc

    daily = data.get("daily") or {}
    times = daily.get("time") or []
    if not times:
        raise WeatherToolError("Weather API returned no forecast days")

    days_out = []
    for i, day in enumerate(times):
        days_out.append(
            {
                "date": day,
                "temp_max_c": _idx(daily.get("temperature_2m_max"), i),
                "temp_min_c": _idx(daily.get("temperature_2m_min"), i),
                "precipitation_mm": _idx(daily.get("precipitation_sum"), i),
                "precip_probability_pct": _idx(
                    daily.get("precipitation_probability_max"), i
                ),
                "weather_code": _idx(daily.get("weather_code"), i),
                "rain_likely": _rain_likely(
                    _idx(daily.get("precipitation_sum"), i),
                    _idx(daily.get("precipitation_probability_max"), i),
                ),
            }
        )
    return {
        "place": place,
        "days": days_out,
        "source": "open-meteo",
        "label": "MCP data",
    }


def _idx(seq: list[Any] | None, i: int) -> Any:
    if not seq or i >= len(seq):
        return None
    return seq[i]


def _rain_likely(precip_mm: Any, prob: Any) -> bool:
    try:
        if precip_mm is not None and float(precip_mm) >= 1.0:
            return True
        if prob is not None and float(prob) >= 50:
            return True
    except (TypeError, ValueError):
        pass
    return False


def format_current(payload: dict[str, Any]) -> str:
    return (
        f"Current weather in {payload.get('place')}: "
        f"{payload.get('temperature_c')}°C, humidity {payload.get('humidity_pct')}%, "
        f"precipitation {payload.get('precipitation_mm')} mm, "
        f"wind {payload.get('wind_speed_kmh')} km/h "
        f"(observed {payload.get('observed_at')}; source {payload.get('source')})."
    )


def format_forecast(payload: dict[str, Any]) -> str:
    lines = [f"Forecast for {payload.get('place')} ({len(payload.get('days') or [])} day(s)):"]
    for d in payload.get("days") or []:
        rain = "rain likely" if d.get("rain_likely") else "rain unlikely"
        lines.append(
            f"- {d.get('date')}: {d.get('temp_min_c')}–{d.get('temp_max_c')}°C, "
            f"precip {d.get('precipitation_mm')} mm "
            f"(prob {d.get('precip_probability_pct')}%) — {rain}"
        )
    return "\n".join(lines)
