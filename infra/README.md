# Infrastructure as code

Composable Docker Compose units. **Knowledge** (Neo4j, Chroma) is Phase **1.5**. **Runtime** (MCP, optional Streamlit) is Phase **6**.

Secrets stay in `.env` (never commit). See [`.env.example`](../.env.example).

## Units

| Path | Phase | Service | Profile | Host |
|------|-------|---------|---------|------|
| `neo4j/` | 1.5 | Neo4j 5 | (default) | 7474 / 7687 |
| `chroma/` | 1.5 | Chroma | (default) | 8000 |
| `kb-pipeline/` | 1.5 | DE → load job | `pipeline` | — |
| `mcp-weather/` | 6 | Weather MCP | `mcp` | — |
| `mcp-currency/` | 6 | Currency MCP | `mcp` | — |
| `app/` | 6 | Streamlit UI | `app` | 8501 |
| `compose.yml` | 1.5+6 | Umbrella `include` | see below | — |

## Quick start

```bash
cp .env.example .env
# set NEO4J_PASSWORD=changeme

# Knowledge only
docker compose -f infra/compose.yml up -d

# Knowledge + MCP sidecars
docker compose -f infra/compose.yml --profile mcp up -d --build

# Knowledge + Streamlit
docker compose -f infra/compose.yml --profile app up -d --build

# Full local demo stack
docker compose -f infra/compose.yml --profile mcp --profile app up -d --build
```

Wait for healthy, then load KB (host CLIs are the default):

```bash
export CHROMA_HOST=localhost CHROMA_PORT=8000 NEO4J_PASSWORD=changeme
python scripts/build_kb.py --embeddings fake --gate   # or openai
python scripts/load_neo4j.py --require-neo4j
```

UI on the host (preferred for LLM keys):

```bash
export LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake MCP_MOCK_MODE=true
streamlit run app/streamlit_app.py
```

Or open http://localhost:8501 when the `app` profile is up.

## Networks for kb-pipeline

```bash
docker compose -f infra/compose.yml up -d
docker compose -f infra/compose.yml --profile pipeline run --rm kb-pipeline \
  python scripts/build_kb.py --embeddings fake
```

## Tear down

```bash
docker compose -f infra/compose.yml --profile mcp --profile app down
# add -v to wipe Neo4j/Chroma volumes
```

## Offline (no Docker)

Leave `CHROMA_HOST` unset (`CHROMA_PATH=data/chroma`), use `python scripts/load_neo4j.py --memory`, and `MCP_MOCK_MODE=true`.

## Agents and MCP

Phase 5 agents call **in-process** weather/currency clients by default (same code as MCP servers). Compose MCP units are for stdio attach / ops parity. Set `MCP_MOCK_MODE=true` when upstream APIs are unavailable — never fabricate temps or FX rates silently.
