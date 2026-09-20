# MCP currency — Phase 6

```bash
docker compose -f infra/mcp-currency/compose.yml --profile mcp up -d --build

# Stdio MCP
docker compose -f infra/mcp-currency/compose.yml --profile mcp run --rm \
  mcp-currency python -m mcp_servers.currency.server
```

Tool: `convert_fx` (Frankfurter / ECB). Use `MCP_MOCK_MODE=true` offline.
