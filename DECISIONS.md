# Decisions log — AI Travel Planning Assistant

Track phase status, gate outcomes, and stack choices. Update at every phase exit.

## Locked stack (Option A)

| Area | Choice |
|------|--------|
| Orchestration | LangChain |
| LLM (toggle) | `openai` \| `gemini` \| `cursor` via `LLM_PROVIDER` + Streamlit sidebar |
| Embeddings | `EMBEDDING_PROVIDER` (default = chat provider) |
| Vector store | Chroma (Phase 1.5 `infra/chroma/` + Phase 4 load) |
| Graph store | Neo4j (Phase 1.5 `infra/neo4j/` + Phase 4 load) |
| UI | Streamlit |
| MCP | Weather + Currency |
| Observability | Generic JSON logs (`src/observability`, `LOG_*` env) |
| Destination | Singapore |
| Knowledge IaC | **Phase 1.5** — Docker Compose per store under `infra/` (**done**) |
| Runtime IaC | **Phase 5–6** — MCP + optional app + umbrella |

## Infrastructure as code

Composable units; start only what you need. Knowledge early so DE load + agent tests share one stack.

**Knowledge (Phase 1.5)** — [`docs/architecture/01b-knowledge-infra.md`](docs/architecture/01b-knowledge-infra.md), [`infra/README.md`](infra/README.md):

| Service | Unit | Status |
|---------|------|--------|
| Neo4j | `infra/neo4j/compose.yml` | **done** |
| Chroma | `infra/chroma/compose.yml` | **done** |
| Umbrella | `infra/compose.yml` | **done** |
| KB pipeline job | `infra/kb-pipeline/Dockerfile` | **done** (optional profile) |

**Runtime (Phase 5–6)** — [`docs/architecture/06-ops-and-acceptance.md`](docs/architecture/06-ops-and-acceptance.md):

| Service | Unit | Status |
|---------|------|--------|
| MCP weather | `infra/mcp-weather/` | **done** (profile `mcp`) |
| MCP currency | `infra/mcp-currency/` | **done** (profile `mcp`) |
| Streamlit app | `infra/app/` | **done** (profile `app`; host Streamlit preferred) |
| LLM APIs | `.env` only | n/a |

Optional umbrella includes knowledge units. Secrets never committed. Agents use the **same** Neo4j/Chroma as Phase 4 load. Set `CHROMA_HOST=localhost` when using Compose Chroma; leave unset for local `data/chroma/`.

## LLM provider key style

- **Pattern:** `LLMProviderAdapter` contract (`src/llm/contract.py`) + adapters (`src/llm/adapters/`) + factory registry switch (`get_adapter` / `get_chat_model` / `get_embeddings`)
- **Toggle:** `LLM_PROVIDER=openai|gemini|cursor|fake` (Streamlit sidebar overrides per session)
- **OpenAI:** `OPENAI_API_KEY`, optional `OPENAI_MODEL` (default `gpt-4o-mini`)
- **Gemini:** `GOOGLE_API_KEY`, optional `GEMINI_MODEL` (default `gemini-2.0-flash`)
- **Cursor:** `CursorAdapter` — `CURSOR_API_KEY` (dashboard Integrations), `CURSOR_LLM_BASE_URL` (local OpenAI-compatible gateway, e.g. `http://localhost:8787/v1`), optional `CURSOR_MODEL` (e.g. `composer-2.5`). Cursor has no official chat-completions API — gateway required. Prefer `EMBEDDING_PROVIDER=openai|fake` for RAG.
- **Embeddings override:** optional `EMBEDDING_PROVIDER` (same enum); re-index Chroma if changed
- **Logging:** `LOG_LEVEL`, `LOG_FORMAT=json|text`, optional `LOG_FILE=logs/app.jsonl`
- Missing key for selected provider → config error; **no silent fallback**

See `.env.example`.

## Current phase

| Field | Value |
|-------|-------|
| Active phase | **complete (0–6)** |
| Last updated | 2026-09-20 |

## Phase gate outcomes

| Phase | Status | Outcome / decision for next phase |
|-------|--------|-----------------------------------|
| 0 Skill + scaffold | **done** | Skill, dirs, overview, USE_CASES, `.env.example`, `requirements.txt`, `.gitignore` present. Proceed to Phase 1. |
| 1 Data pipeline | **done** | 4 sources in `data/sources.yaml`; coverage matrix maps all required topics; ingest/normalize + gate tests pass. Topics still `planned` until crawl. **Decision:** proceed to Phase 2 targeted crawl of allowlisted seeds; Visit Singapore ToS → manual dump fallback if blocked. Infra contract for load target documented in Phase 1.5. |
| 1.5 Knowledge IaC | **done** | Compose `infra/neo4j/` + `infra/chroma/` + umbrella `infra/compose.yml`; optional `kb-pipeline` image; `CHROMA_HOST` client support; `tests/test_phase15_infra.py`. Live load: start infra then Phase 4 CLIs. |
| 2 Crawl | **done** | Allowlisted BFS crawl (`src/crawl/`, `scripts/crawl.py`): `max_depth=null` (unbounded) + `max_pages=100` per source; Visit Singapore stored as educational excerpts. Live Wikivoyage often HTTP 403 and Visit Singapore thin SPA → committed `data/manual/` dumps installed automatically; required + optional topic buckets green after normalize. **Decision:** clear place/district/transport entities in dumps → proceed to Phase 3 full ontology. |
| 3 Ontology | **done** | Taxonomy + schema + gazetteer; `ontology/entities.json` has 37 entities, 20 spot-checked with evidence; all 5 classes covered. **Decision:** dense typed graph → Phase 4 hybrid (Chroma + Neo4j GraphRAG). |
| 4 Stores | **done (offline + live-ready)** | Chroma KB + HybridRetriever; Neo4j loader with in-memory fallback; offline smoke with `--embeddings fake`. Live path: Phase 1.5 Compose + `CHROMA_HOST` + `load_neo4j.py --require-neo4j`. **Decision:** keep **hybrid** for Phase 5 A1/A4. |
| 5 Agents | **done** | A0–A4 + MCP weather/currency (Open-Meteo / Frankfurter + mock) + Streamlit UI; hybrid RAG reused from Phase 4; use-case suite under `tests/use_cases/`. **Decision:** MCP Compose + README polish in Phase 6; keep hybrid retrieval. |
| 6 Deliverables + runtime IaC | **done** | `infra/mcp-weather`, `infra/mcp-currency`, `infra/app` + umbrella profiles; `DEMO_CHECKLIST.md`, `SAMPLE_QA.md`; acceptance mapped in `06-ops-and-acceptance.md`. |

## Retrieval mode (set after Phase 3–4)

| Field | Value |
|-------|-------|
| Mode | `hybrid` |
| Rationale | Phase 4 smoke: Chroma citations + ontology graph expansion (Neo4j when `NEO4J_PASSWORD` set, else in-memory) both return hits for attraction/transport/district queries. |

## Notes

- Assignment brief: `Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`
- Project skill: `.cursor/skills/travel-assistant-pipeline/SKILL.md`
- Architecture overview: `docs/architecture/00-overview.md`
- Phase 2 crawl note: Wikimedia often returns HTTP 403 for `robots.txt` to some clients; crawler treats missing/forbidden robots as allow (urllib-compatible) and still uses `data/manual/` when page fetch fails.
- Phase 2 spider upgrade: unbounded BFS (`max_depth: null`) capped by `max_pages: 100` per source; ARR Visit Singapore pages remain Markdown excerpts (not full HTML mirrors).
- Phase 2 Singapore scope: Wikivoyage BFS limited via `url_path_prefixes` / `url_path_contains` so crawl stays on Singapore pages, not the whole wiki.
- IaC split: knowledge stores = Phase 1.5 (**implemented** under `infra/`); MCP/app/umbrella = Phase 6 (`06-ops-and-acceptance.md`).
