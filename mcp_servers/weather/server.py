"""MCP weather server entry (stdio FastMCP)."""

from __future__ import annotations

from mcp_servers.weather.tools import (
    fetch_current_weather,
    fetch_forecast,
    format_current,
    format_forecast,
)


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("singapore-weather")

    @mcp.tool()
    def get_current_weather(place: str = "Singapore") -> str:
        """Return current weather for Singapore (or named place using Singapore coords)."""
        payload = fetch_current_weather(place=place or "Singapore")
        return format_current(payload)

    @mcp.tool()
    def get_weather_forecast(days: int = 3, place: str = "Singapore") -> str:
        """Return a multi-day weather forecast for Singapore."""
        payload = fetch_forecast(days=days, place=place or "Singapore")
        return format_forecast(payload)

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
