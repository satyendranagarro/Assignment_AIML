# Architecture — Phase 5: Agents, MCP tools, and Streamlit UI

## Purpose

Wire **intent-routed agents** on top of the Phase 4 **HybridRetriever** (same Chroma + Neo4j as Phase 1.5 load), add **MCP weather + currency** tools, and ship a **Streamlit** chat UI with LLM provider toggle and multi-turn session memory.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Retriever | `src/agents/runtime.py` → Phase 4 stores | Shared KB path |
| Agents | `src/agents/` (A0–A4) | Route, RAG, weather, FX, combined |
| Prompts | `src/prompts/` | Grounding templates |
| MCP tools | `mcp_servers/weather/`, `mcp_servers/currency/` | Live Open-Meteo / Frankfurter + mock |
| UI | `app/streamlit_app.py` | Chat + sidebar provider toggle |
| Use cases | `tests/use_cases/`, `docs/USE_CASES.md` | Pass bar |

## Agent catalog

```text
User → Streamlit → OrchestratorAgent (A0)
                      ├─ classify_intent (deterministic)
                      ├─ SessionState (family / budget / indoor …)
                      ├─ RAGKnowledgeAgent (A1) → HybridRetriever
                      ├─ WeatherToolAgent (A2) → WeatherClient → Open-Meteo
                      ├─ CurrencyToolAgent (A3) → CurrencyClient → Frankfurter
                      └─ CombinedPlannerAgent (A4) → A1 + A2/A3
```

| ID | Intent(s) | Behavior |
|----|-----------|----------|
| A0 | all | Route + memory; out-of-scope / clarify |
| A1 | `rag_only` | KB facts + citations; **no MCP**; gap if empty/foreign |
| A2 | `weather_only` | MCP current/forecast; label `[MCP data]`; never fake temps |
| A3 | `currency_only` | MCP convert; use session budget when amount missing |
| A4 | `combined_itinerary`, `combined_budget` | Day-wise plan; KB + weather and/or FX; labels |

### Response contract

Every substantive answer uses labeled blocks (chat-style body under each label):

- `[KB fact]` — grounded reply synthesized from retrieval (with title/URL citations); not a raw chunk dump
- `[MCP data]` — weather or FX from MCP clients
- `[LLM suggestion]` — planning advice when needed (not a substitute for KB/MCP)
- `[Error]` / `[System]` — failures and scope messages

### Intent set

`rag_only` | `weather_only` | `currency_only` | `combined_itinerary` | `combined_budget` | `clarify` | `out_of_scope`

Routing is **deterministic** (keyword rules in `src/agents/router.py`) so UC-ROUTE tests do not depend on an LLM.

## MCP design

| Tool | Live upstream | Mock (`MCP_MOCK_MODE=true`) | Failure |
|------|---------------|----------------------------|---------|
| Weather | Open-Meteo forecast API | Documented Singapore mock days | Explicit error; **no** fabricated °C |
| Currency | Frankfurter (ECB) | Documented INR/SGD/USD rates | Explicit error; **no** fabricated rates |

In-process clients are the default for agents (no separate stdio required). Optional FastMCP stdio servers:

```bash
python -m mcp_servers.weather.server
python -m mcp_servers.currency.server
```

## LLM toggle

Agents call only `src/llm/factory.py`. Streamlit sidebar sets `st.session_state.llm_provider`. Missing key → `ConfigError` surfaced to the user; **no silent provider fallback**.

## Observability

Events: `request.*`, `agent.*`, `retrieve.*`, `mcp.call` / `mcp.error`, `llm.invoke` / `llm.error`, `llm.provider_changed`, `config_error` via `src/observability`.

## How to run

```bash
# Knowledge stores (Phase 1.5) already loaded from Phase 4, or offline Chroma:
# export EMBEDDING_PROVIDER=fake   # if index built with fake embeddings

# Demo with mock MCP (no network for tools)
export LLM_PROVIDER=fake
export EMBEDDING_PROVIDER=fake
export MCP_MOCK_MODE=true
streamlit run app/streamlit_app.py

# Use-case / unit suite (offline)
pytest tests/test_phase5_agents.py tests/use_cases/ -q
```

## Exit criteria (gate → Phase 6)

- [x] A0–A4 implemented with intent routing + session memory
- [x] Hybrid RAG answers include citations; no invented KB facts
- [x] Weather + currency MCP clients (live + mock + hard-fail)
- [x] Combined itinerary includes RAG + weather + day-wise + labels (UC-COMBO-01)
- [x] Streamlit UI with LLM sidebar toggle
- [x] Use-case suite covers ROUTE / NEG / LLM / COMBO-01 + RAG/WX/FX/MEM samples
- [x] This architecture doc updated in-phase

### Decision table (Phase 5 → 6)

| Observation | Action in Phase 6 |
|-------------|-------------------|
| MCP flaky offline | Document `MCP_MOCK_MODE`; ship Compose for MCP servers |
| Prompt mixups | Tighten prompts; keep label contract |
| Retrieval miss | Regress to Phase 4 chunk/index before polish |
| Use-case bar green | README demo path + MCP/app Compose umbrella |

## Phase 5 status

**Complete (offline use-case bar).** Live Open-Meteo/Frankfurter work when `MCP_MOCK_MODE=false` and network is available. Phase 6 adds runtime IaC (`infra/mcp-*`, optional app) and acceptance polish.
