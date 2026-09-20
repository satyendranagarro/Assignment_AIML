# Decisions log — AI Travel Planning Assistant

Track phase status, gate outcomes, and stack choices. Update at every phase exit.

## Locked stack (Option A)

| Area | Choice |
|------|--------|
| Orchestration | LangChain |
| LLM (toggle) | `openai` \| `gemini` \| `cursor` via `LLM_PROVIDER` + Streamlit sidebar |
| Embeddings | `EMBEDDING_PROVIDER` (default = chat provider) |
| Vector store | Chroma (`data/chroma/`) |
| Graph store | Neo4j |
| UI | Streamlit |
| MCP | Weather + Currency |
| Observability | Generic JSON logs (`src/observability`, `LOG_*` env) |
| Destination | Singapore |

## LLM provider key style

- **Toggle:** `LLM_PROVIDER=openai|gemini|cursor` (Streamlit sidebar overrides per session)
- **OpenAI:** `OPENAI_API_KEY`, optional `OPENAI_MODEL` (default `gpt-4o-mini`)
- **Gemini:** `GOOGLE_API_KEY`, optional `GEMINI_MODEL` (default `gemini-2.0-flash`)
- **Cursor:** `CURSOR_API_KEY`, `CURSOR_LLM_BASE_URL` (OpenAI-compatible), optional `CURSOR_MODEL`
- **Embeddings override:** optional `EMBEDDING_PROVIDER` (same enum); re-index Chroma if changed
- **Logging:** `LOG_LEVEL`, `LOG_FORMAT=json|text`, optional `LOG_FILE=logs/app.jsonl`
- Missing key for selected provider → config error; **no silent fallback**

See `.env.example`.

## Current phase

| Field | Value |
|-------|-------|
| Active phase | **5 — Agents** |
| Last updated | 2026-09-20 |

## Phase gate outcomes

| Phase | Status | Outcome / decision for next phase |
|-------|--------|-----------------------------------|
| 0 Skill + scaffold | **done** | Skill, dirs, overview, USE_CASES, `.env.example`, `requirements.txt`, `.gitignore` present. Proceed to Phase 1. |
| 1 Data pipeline | **done** | 4 sources in `data/sources.yaml`; coverage matrix maps all required topics; ingest/normalize + gate tests pass. Topics still `planned` until crawl. **Decision:** proceed to Phase 2 targeted crawl of allowlisted seeds; Visit Singapore ToS → manual dump fallback if blocked. |
| 2 Crawl | **done** | Allowlisted BFS crawl (`src/crawl/`, `scripts/crawl.py`): `max_depth=null` (unbounded) + `max_pages=100` per source; Visit Singapore stored as educational excerpts. Live Wikivoyage often HTTP 403 and Visit Singapore thin SPA → committed `data/manual/` dumps installed automatically; required + optional topic buckets green after normalize. **Decision:** clear place/district/transport entities in dumps → proceed to Phase 3 full ontology. |
| 3 Ontology | **done** | Taxonomy + schema + gazetteer; `ontology/entities.json` has 37 entities, 20 spot-checked with evidence; all 5 classes covered. **Decision:** dense typed graph → Phase 4 hybrid (Chroma + Neo4j GraphRAG). |
| 4 Stores | **done** | Chroma KB + HybridRetriever; Neo4j loader with in-memory fallback; retrieval smoke + graph checks pass offline (`--embeddings fake`). **Decision:** graph expansions useful → keep **hybrid** for Phase 5 A1/A4. |
| 5 Agents | pending | — |
| 6 Deliverables | pending | — |

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
