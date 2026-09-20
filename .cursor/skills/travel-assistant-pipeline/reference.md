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

| Value | Chat | Env |
|-------|------|-----|
| `openai` | ChatOpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `gemini` | ChatGoogleGenerativeAI | `GOOGLE_API_KEY`, `GEMINI_MODEL` |
| `cursor` | OpenAI-compatible → Cursor gateway | `CURSOR_API_KEY`, `CURSOR_LLM_BASE_URL`, `CURSOR_MODEL` |

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
src/llm/, observability/, rag/, graph/, agents/, prompts/
app/streamlit_app.py
logs/   # gitignored
tests/use_cases/
docs/architecture/00–06, USE_CASES.md
```
