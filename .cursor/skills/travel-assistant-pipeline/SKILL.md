---
name: travel-assistant-pipeline
description: >-
  Phase-gated build of the Singapore AI Travel Planning Assistant (RAG + Neo4j +
  MCP weather/currency + LangChain agents). Use when implementing or continuing
  any phase of this project, updating the knowledge-base pipeline, agents,
  ontology, vector/graph stores, use-case tests, architecture docs, or Phase 6
  per-service infra (Compose under infra/). Use also for Phase 1.5 knowledge
  IaC (infra/neo4j, infra/chroma) shared by DE load and agents.
---

# Travel Assistant Pipeline

## When to use

Apply this skill for any work on the NAGP_AIML travel assistant: data pipeline, crawl, ontology, Chroma/Neo4j, agents, MCP tools, Streamlit UI, use cases, architecture documentation, or Phase 1.5/6 infra.

## Locked stack (A)

- Orchestration: LangChain
- **LLM (toggleable):** `openai` | `gemini` | `cursor` via `LLM_PROVIDER` and Streamlit sidebar
- Embeddings: follow `EMBEDDING_PROVIDER` (default = chat provider)
- Vector store: Chroma (Phase 1.5 `infra/chroma/` → Phase 4 load → Phase 5 agents)
- Graph store: Neo4j (Phase 1.5 `infra/neo4j/` → Phase 4 load → Phase 5 agents)
- UI: Streamlit
- Live tools: MCP weather + MCP currency
- Observability: generic JSON structured logging (`src/observability`)
- Destination: Singapore

## LLM toggle rules

1. Agents call only `src/llm/factory.py` (`get_chat_model` / `get_embeddings` / `get_adapter`).
2. Resolution order: explicit kwarg → Streamlit session → `LLM_PROVIDER` env → default `openai`.
3. Missing key for selected provider → `config_error`; never silent fallback to another provider.
4. **Adapter contract:** `src/llm/contract.py` (`LLMProviderAdapter`) — each provider is `src/llm/adapters/*`; factory switches via registry. Add a provider by implementing the contract + registering in `ADAPTERS`.
5. `cursor` = `CursorAdapter` → **online default:** `cursor-sdk` `Agent.prompt` (cloud no-repo or local scratch). Optional gateway: `CURSOR_USE_GATEWAY=true` + `CURSOR_LLM_BASE_URL`. Prefer separate `EMBEDDING_PROVIDER` for RAG.

## Observability rules

1. Use `src/observability` for all request/agent/retrieve/MCP/LLM events.
2. Include `correlation_id`, `session_id`, `llm_provider` on every structured log.
3. Do not log API keys; truncate user text at INFO (full preview only at DEBUG).
4. Config: `LOG_LEVEL`, `LOG_FORMAT=json|text`, optional `LOG_FILE=logs/app.jsonl`.

## Before coding

1. Read `DECISIONS.md` for current phase and gate outcomes.
2. Read the matching `docs/architecture/0N-*.md` for that phase.
3. Do not skip phases or exit criteria. If a gate fails, stay on the phase or regress per the decision table.
4. Never invent destination facts or fabricate MCP results.
5. Wire chat/embeddings only through `src/llm/factory.py`; emit logs via `src/observability`.
6. **Knowledge infra:** Phase 1.5 before live load/agent tests; agents must use the same Neo4j/Chroma as Phase 4.

## Phase order and gates

| Phase | Name | Architecture doc | Exit before next |
|-------|------|------------------|------------------|
| 0 | Skill + scaffold | `docs/architecture/00-overview.md` | Skill, scaffold, overview, USE_CASES skeleton |
| 1 | Data engineering | `docs/architecture/01-data-pipeline.md` | ≥3 sources + coverage matrix |
| **1.5** | **Knowledge IaC** | `docs/architecture/01b-knowledge-infra.md` | Neo4j + Chroma Compose healthy; env contract |
| 2 | Crawl | `docs/architecture/02-crawl.md` | Topic buckets green; crawl reproducible |
| 3 | Ontology / taxonomy | `docs/architecture/03-ontology.md` | Taxonomy + ≥20 entities spot-checked |
| 4 | Load into infra | `docs/architecture/04-stores.md` | Live retrieval preferred; offline fallback for CI |
| 5 | Agents + MCP + UI | `docs/architecture/05-agents.md` | Use-case pass bar (**same** KB infra) |
| 6 | Deliverables + runtime IaC | `docs/architecture/06-ops-and-acceptance.md` | README, demo, MCP/app/umbrella |

### Decision gates (summary)

- **Phase 1 → 1.5:** registry ready → stand up knowledge Compose before live store tests.
- **Phase 1 → 2:** gaps → targeted crawl; ToS block → manual dump; thin → more URLs; full → light refresh (file work OK without Docker).
- **Phase 1.5 → 4:** stores healthy → Phase 4 loads into them; Docker missing → offline fallback only.
- **Phase 2 → 3:** clear entities → full ontology; unstructured → light tags; dupes → merge first.
- **Phase 3 → 4:** dense graph → GraphRAG; sparse → Chroma primary; poor extract → seed + vector-only.
- **Phase 4 → 5:** graph helps → hybrid; noisy → Chroma-only; bad chunks → retune first; **reuse Phase 1.5 infra**.
- **Phase 5 → 6:** MCP flaky → mock mode docs; prompt mixups → tighten; retrieval miss → regress to Phase 4.

## Knowledge + runtime IaC

```text
1.5  infra/neo4j + infra/chroma (+ optional kb-pipeline)
4    build_kb + load_neo4j → into 1.5
5    agents → same stores; add MCP servers
6    infra/mcp-* + optional app + umbrella compose
```

Offline: `--embeddings fake`, `--memory`. Details: `01b-knowledge-infra.md`, `06-ops-and-acceptance.md`.

## Agent catalog (A0–A4)

| ID | Agent | Role |
|----|-------|------|
| A0 | OrchestratorAgent | Intent route; multi-turn state; out-of-scope |
| A1 | RAGKnowledgeAgent | Grounded KB answers + citations; no MCP for static facts |
| A2 | WeatherToolAgent | MCP weather/forecast; label MCP; no fake weather |
| A3 | CurrencyToolAgent | MCP convert; label MCP; no fake rates |
| A4 | CombinedPlannerAgent | RAG + weather and/or currency; day-wise plan; label KB / MCP / LLM |

Intents: `rag_only` | `weather_only` | `currency_only` | `combined_itinerary` | `combined_budget` | `clarify` | `out_of_scope`.

Response contract: label `KB fact`, `MCP data`, `LLM suggestion`.

## Use-case pass bar (Phase 5)

Must pass: **UC-COMBO-01**, all **UC-ROUTE-***, all **UC-NEG-***, **UC-LLM-01..04**, plus ≥4 RAG, ≥2 WX, ≥2 FX, ≥2 MEM. Full table: `docs/USE_CASES.md`.

## Documentation rule

In the same phase as the build, update that phase’s `docs/architecture/0N-*.md`. Do not leave architecture docs for Phase 6 only.

## After code changes

Run `graphify update .` (AST-only) to keep `graphify-out/` current.
