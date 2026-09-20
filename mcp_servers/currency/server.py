"""MCP currency server entry (stdio FastMCP)."""

from __future__ import annotations

from mcp_servers.currency.tools import convert_currency, format_conversion


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("singapore-currency")

    @mcp.tool()
    def convert_fx(amount: float, from_currency: str, to_currency: str) -> str:
        """Convert an amount between currencies (e.g. INR to SGD)."""
        payload = convert_currency(amount, from_currency, to_currency)
        return format_conversion(payload)

    return mcp


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
