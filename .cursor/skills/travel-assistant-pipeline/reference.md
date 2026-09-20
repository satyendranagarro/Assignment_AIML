# Travel assistant pipeline — reference

Companion to `SKILL.md`. Keep URLs and schemas here so the skill stays short.

## Recommended Singapore sources (Phase 1 registry)

Exact URLs live in [`data/sources.yaml`](../../../data/sources.yaml). Coverage: [`data/coverage_matrix.yaml`](../../../data/coverage_matrix.yaml).

| Source | Intended coverage |
|--------|-------------------|
| Wikivoyage Singapore Travel Guide | Districts, attractions, transport, food, practical, itineraries |
| Visit Singapore — Essential Travel Information | Climate, language, connectivity, services |
| Visit Singapore — Sample Itineraries | Duration / profile itineraries |
| Visit Singapore — Things to Do | Attractions by interest |

Retain `title` + `url` metadata for citations. Respect each site’s reuse terms.

## Ontology sketch (Phase 3)

**Classes:** `Attraction`, `District`, `ItineraryDay`, `TransportMode`, `Tip`

**Relations:** `located_in`, `suitable_for`, `nearby`, `part_of_itinerary`

**Tags:** `indoor`, `outdoor`, `family`, `culture`, `food`, `transport`

## Agent intents (Phase 5)

`rag_only` | `weather_only` | `currency_only` | `combined_itinerary` | `combined_budget` | `clarify` | `out_of_scope`

## LLM providers (toggle)

Contract: `LLMProviderAdapter` in `src/llm/contract.py`. Registry: `src/llm/adapters.ADAPTERS`. Factory: `get_adapter` / `get_chat_model` / `get_embeddings`.

| Value | Adapter | Env |
|-------|---------|-----|
| `openai` | `OpenAIAdapter` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `gemini` | `GeminiAdapter` | `GOOGLE_API_KEY`, `GEMINI_MODEL` |
| `cursor` | `CursorAdapter` → local gateway | `CURSOR_API_KEY`, `CURSOR_LLM_BASE_URL` (e.g. `http://localhost:8787/v1`), `CURSOR_MODEL` (e.g. `composer-2.5`); use separate `EMBEDDING_PROVIDER` for RAG |
| `fake` | `FakeAdapter` | none (offline tests) |

Resolution: kwarg → Streamlit session → `LLM_PROVIDER` → default `openai`. No silent fallback.

## Observability events

`request.start/end` · `llm.provider_changed` · `agent.start/end` · `retrieve.start/end` · `mcp.call/error` · `llm.invoke/error` · `config_error`

Fields: `correlation_id`, `session_id`, `llm_provider`, `agent`, `intent`, `latency_ms`, `status`

## Use-case ID prefixes

`UC-RAG` · `UC-WX` · `UC-FX` · `UC-COMBO` · `UC-ROUTE` · `UC-MEM` · `UC-NEG` · `UC-LLM`

Full table: [`docs/USE_CASES.md`](../../../docs/USE_CASES.md)

## Directory map

```text
data/sources.yaml, raw/, processed/, chroma/, coverage_matrix.yaml
ontology/taxonomy.yaml, schema.json, entities.json
scripts/ingest.py, crawl.py, normalize.py, build_kb.py, load_neo4j.py, eval_retrieval.py
mcp_servers/weather/, currency/
infra/neo4j/, chroma/, compose.yml, kb-pipeline/   # Phase 1.5 knowledge IaC
infra/mcp-weather/, mcp-currency/, app/            # Phase 6 runtime IaC
src/llm/, observability/, rag/, graph/, agents/, prompts/
app/streamlit_app.py
logs/   # gitignored
tests/use_cases/
docs/architecture/00–06 (+ 01b), USE_CASES.md, DEMO_CHECKLIST.md, SAMPLE_QA.md
```

## IaC units

**Phase 1.5 (knowledge — load + agents share these):**

| Path | Service |
|------|---------|
| `infra/neo4j/compose.yml` | Neo4j graph store |
| `infra/chroma/compose.yml` | Chroma vector server |
| `infra/compose.yml` | Umbrella + profiles |
| `infra/kb-pipeline/Dockerfile` | Optional DE → load job |

Set `CHROMA_HOST=localhost` when using Compose Chroma; leave unset for `CHROMA_PATH=data/chroma`.

**Phase 6 (runtime):**

| Path | Service | Profile |
|------|---------|---------|
| `infra/mcp-weather/` | Weather MCP | `mcp` |
| `infra/mcp-currency/` | Currency MCP | `mcp` |
| `infra/app/` | Optional Streamlit | `app` |

See [`01b-knowledge-infra.md`](../../../docs/architecture/01b-knowledge-infra.md) and [`06-ops-and-acceptance.md`](../../../docs/architecture/06-ops-and-acceptance.md).
