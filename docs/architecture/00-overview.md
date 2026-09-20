# Architecture overview — Phase 0

## Purpose

Context-aware **AI Travel Planning Assistant** for **Singapore** that combines:

1. A **document knowledge base** (RAG over Chroma, optional Neo4j expansion)
2. **Current information** via **MCP** (weather + currency)
3. **Combined** answers (e.g. weather-aware three-day itinerary)

Source of truth for product requirements: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](../../Requirement/AI_Travel_Planning_Assistant_Assignment.pdf).

## System context

```text
User → Streamlit UI → OrchestratorAgent (A0)
                         ├─ RAGKnowledgeAgent (A1) → HybridRetriever → Chroma + Neo4j
                         ├─ WeatherToolAgent (A2) → MCP Weather
                         ├─ CurrencyToolAgent (A3) → MCP Currency
                         └─ CombinedPlannerAgent (A4) → A1 + A2/A3

KB build (Phases 1–4):
  sources.yaml → crawl/normalize → ontology/taxonomy → chunk/embed → Chroma
                                                       entity graph → Neo4j
```

## Stack A (locked)

| Layer | Technology |
|-------|------------|
| Orchestration | LangChain |
| LLM (toggle) | OpenAI · Gemini · Cursor (OpenAI-compatible) |
| Embeddings | Via `EMBEDDING_PROVIDER` (default = chat provider) |
| Vector DB | Chroma |
| Graph DB | Neo4j |
| UI | Streamlit (sidebar LLM toggle) |
| Tools | MCP weather, MCP currency |
| Observability | Generic JSON structured logs |

See [`DECISIONS.md`](../../DECISIONS.md) and [`.env.example`](../../.env.example).

### LLM toggle

`LLM_PROVIDER=openai|gemini|cursor` plus Streamlit sidebar override. Factory: `src/llm/factory.py`. No silent fallback if the selected provider’s key is missing.

### Observability

`src/observability` emits `request.*`, `agent.*`, `retrieve.*`, `mcp.*`, `llm.*` with `correlation_id` / `llm_provider`. Config: `LOG_LEVEL`, `LOG_FORMAT`, `LOG_FILE`.

## Phase gate summary

| Phase | Deliverable | Gate |
|-------|-------------|------|
| 0 | Skill, scaffold, this overview, USE_CASES skeleton | Present before Phase 1 |
| 1 | Ingest/normalize + coverage matrix | ≥3 sources with citations metadata |
| 2 | Allowlisted crawl | Topic coverage green |
| 3 | Ontology + taxonomy | Validated entities |
| 4 | Chroma + Neo4j + retriever | Retrieval smoke tests |
| 5 | Agents + MCP + UI + UC runs | Use-case pass bar |
| 6 | README, samples, demo, ops doc | Assignment deliverables 15–20 |

Decision tables that choose the *shape* of the next phase live in the project skill and in each phase architecture doc.

## Agents (preview)

| ID | Name | Responsibility |
|----|------|----------------|
| A0 | OrchestratorAgent | Intent routing + conversation state |
| A1 | RAGKnowledgeAgent | Grounded destination Q&A + citations |
| A2 | WeatherToolAgent | Forecast/current via MCP |
| A3 | CurrencyToolAgent | FX conversion via MCP |
| A4 | CombinedPlannerAgent | Day-wise plans merging RAG + MCP |

Full behavior and sequence diagrams: `05-agents.md` (Phase 5).

## Out of scope

Flight/hotel booking, payments, route navigation, reservations.

## Acceptance criteria (assignment)

- [ ] KB from ≥3 travel resources
- [ ] Embedding-based semantic retrieval
- [ ] Grounded answers with source references
- [ ] Weather via MCP
- [ ] Currency via MCP
- [ ] ≥1 combined RAG + MCP response
- [ ] Multi-turn context retained
- [ ] Intent-based tool selection
- [ ] Clear handling of missing KB / tool failures
- [ ] Simple usable UI

Mapped to use-case IDs in [`docs/USE_CASES.md`](../USE_CASES.md).

## Related docs

| Doc | Phase |
|-----|-------|
| `01-data-pipeline.md` | 1 |
| `02-crawl.md` | 2 |
| `03-ontology.md` | 3 |
| `04-stores.md` | 4 |
| `05-agents.md` | 5 |
| `06-ops-and-acceptance.md` | 6 |

## Phase status

- **Phase 0 — Complete.** Skill, scaffold, this overview, USE_CASES, README, DECISIONS, `.env.example`, `requirements.txt`, `.gitignore`.
- **Phase 1 — Complete.** See [`01-data-pipeline.md`](01-data-pipeline.md): `data/sources.yaml` (≥3 sources), `data/coverage_matrix.yaml`, `scripts/ingest.py` / `normalize.py`, `src/data/`.
- **Phase 2 — Complete.** See [`02-crawl.md`](02-crawl.md): allowlisted crawl, manual fallbacks, topic buckets green. Next: Phase 3 ontology (`03-ontology.md`).
