# Architecture — Phase 1.5: Knowledge store IaC

## Purpose

Stand up **composable infrastructure** for the knowledge layer **before** Phase 4 load and Phase 5 agents, so:

1. The data-engineering path can **load** processed docs + ontology into real stores.
2. Pipeline / store tests can run **against that infra** (not only in-memory / local-file fallbacks).
3. Agents later **reuse the same** Neo4j + Chroma endpoints and volumes — one knowledge stack.

This phase is **infra only** (Compose units + healthchecks + env contract). Crawl/normalize stay Phases 1–2; ontology Phase 3; **load** is Phase 4.

## Why before Phase 2–4 content work (plan order)

```text
Phase 1   registry + normalize contract (files)
Phase 1.5 infra/neo4j + infra/chroma (+ optional kb-pipeline)  ← YOU ARE HERE
Phase 2–3 crawl + ontology → artifacts on volumes
Phase 4   build_kb + load_neo4j → INTO Phase 1.5 infra
Phase 5   agents → SAME infra
Phase 6   MCP/app IaC + umbrella + deliverables
```

If Phase 1–4 app code already exists, treat 1.5 as a **required backfill** before calling the live-store path “done” for demos and agent tests.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Neo4j Compose | `infra/neo4j/` | Graph store; `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` |
| Chroma Compose | `infra/chroma/` | Vector store service + persistent volume (or bind `data/chroma/`) |
| Optional job | `infra/kb-pipeline/` | One-shot/job image to run ingest→crawl→normalize→ontology→build_kb→load |
| Env contract | `.env.example` | Document vars owned by knowledge units |
| Volumes | `data/raw`, `data/processed`, `data/chroma`, `ontology/` | Persist KB artifacts |

**Not in this phase:** MCP weather/currency, Streamlit app (Phase 5–6).

## Principles

1. **Separate units** — start Neo4j without Chroma (or vice versa) when debugging.
2. **Same stack for load and agents** — Phase 4 writes; Phase 5 reads; no second Neo4j/Chroma.
3. **Offline fallback remains** — `--embeddings fake`, `--memory`, host-local `data/chroma/` for CI without Docker.
4. **Secrets in `.env`** — never commit passwords.

## Env contract (knowledge)

| Var | Owner | Notes |
|-----|--------|--------|
| `NEO4J_URI` | `infra/neo4j/` | Default `bolt://localhost:7687` |
| `NEO4J_USER` | `infra/neo4j/` | Default `neo4j` |
| `NEO4J_PASSWORD` | `infra/neo4j/` | Required for live graph load |
| `CHROMA_PATH` / server URL | `infra/chroma/` | Persist collection `singapore_kb`; align with `src/rag` |
| `EMBEDDING_PROVIDER` | app / pipeline | Used at load time (Phase 4), not by Compose itself |

## Suggested commands (when implemented)

```bash
docker compose -f infra/neo4j/compose.yml up -d
docker compose -f infra/chroma/compose.yml up -d
# healthcheck bolt + chroma HTTP/heartbeat
# then Phase 2–4 CLIs (host or infra/kb-pipeline)
```

## Exit criteria (gate → Phase 2, or unlock Phase 4 live path)

- [ ] `infra/neo4j/` up/down documented; bolt healthcheck passes
- [ ] `infra/chroma/` up/down documented; volume persists across restart
- [ ] `.env.example` lists knowledge vars; README links start order
- [ ] Optional `infra/kb-pipeline/` documented (or explicit “host CLIs OK”)
- [ ] Note in `DECISIONS.md`: knowledge IaC = Phase 1.5; MCP/app = Phase 5–6
- [ ] Smoke: can connect from host with `NEO4J_*` (and Chroma client settings)

### Decision table (Phase 1.5 → next)

| Observation | Action |
|-------------|--------|
| Neo4j healthy | Proceed crawl/ontology; Phase 4 uses `--require-neo4j` for live gate |
| Chroma volume OK | Phase 4 `build_kb` targets this unit |
| Docker unavailable | Keep offline fallback; do not block Phase 2–3 file work |
| Agents need KB | Must use **same** Compose project/env as Phase 4 load |

## Phase 1.5 status

**Planned.** Implement Compose units before relying on live Neo4j/Chroma for pipeline or agent tests. See also Phase 4 load ([`04-stores.md`](04-stores.md)) and Phase 6 ops umbrella ([`06-ops-and-acceptance.md`](06-ops-and-acceptance.md)).
