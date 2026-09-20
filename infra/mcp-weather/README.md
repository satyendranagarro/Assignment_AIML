# MCP weather — Phase 6

```bash
# Sidecar / health mode (Compose profile `mcp`)
docker compose -f infra/mcp-weather/compose.yml --profile mcp up -d --build

# Stdio MCP (for Cursor / Claude Desktop MCP host)
docker compose -f infra/mcp-weather/compose.yml --profile mcp run --rm \
  mcp-weather python -m mcp_servers.weather.server
```

Tools: `get_current_weather`, `get_weather_forecast` (Open-Meteo).  
Set `MCP_MOCK_MODE=true` for documented mock payloads without network.
