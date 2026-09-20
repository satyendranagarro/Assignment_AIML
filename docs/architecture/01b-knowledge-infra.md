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

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Neo4j Compose | `infra/neo4j/compose.yml` | Graph store; `NEO4J_*` |
| Chroma Compose | `infra/chroma/compose.yml` | Vector server; `CHROMA_HOST` / `CHROMA_PORT` |
| Umbrella | `infra/compose.yml` | Include both + optional `kb-pipeline` profile |
| Pipeline image | `infra/kb-pipeline/Dockerfile` | Optional one-shot load job |
| Env contract | `.env.example` | Knowledge vars documented |
| Runbook | `infra/README.md` | Up / down / host CLI load |

**Not in this phase:** MCP weather/currency, Streamlit app (Phase 5–6).

## Principles

1. **Separate units** — start Neo4j without Chroma (or vice versa) when debugging.
2. **Same stack for load and agents** — Phase 4 writes; Phase 5 reads; no second Neo4j/Chroma.
3. **Offline fallback remains** — unset `CHROMA_HOST`, use `CHROMA_PATH=data/chroma`; `--memory` for graph.
4. **Secrets in `.env`** — never commit passwords.

## Env contract (knowledge)

| Var | Owner | Notes |
|-----|--------|--------|
| `NEO4J_URI` | `infra/neo4j/` | Default `bolt://localhost:7687` |
| `NEO4J_USER` | `infra/neo4j/` | Default `neo4j` |
| `NEO4J_PASSWORD` | `infra/neo4j/` | Required for Compose + live load |
| `CHROMA_HOST` | `infra/chroma/` | e.g. `localhost`; empty = local `CHROMA_PATH` |
| `CHROMA_PORT` | `infra/chroma/` | Default `8000` |
| `CHROMA_PATH` | local offline | Used when `CHROMA_HOST` unset |

`src/rag/chroma_store.py` switches to `chromadb.HttpClient` when `CHROMA_HOST` is set.

## How to run

```bash
cp .env.example .env   # set NEO4J_PASSWORD=changeme
docker compose -f infra/compose.yml up -d
# or: docker compose -f infra/neo4j/compose.yml up -d
#     docker compose -f infra/chroma/compose.yml up -d

export CHROMA_HOST=localhost CHROMA_PORT=8000
python scripts/build_kb.py --embeddings fake --gate
python scripts/load_neo4j.py --require-neo4j

pytest tests/test_phase15_infra.py -q
```

Optional pipeline profile: see `infra/kb-pipeline/README.md`.

## Exit criteria (gate)

- [x] `infra/neo4j/` up/down documented; bolt healthcheck in Compose
- [x] `infra/chroma/` up/down documented; persistent volume + healthcheck
- [x] `.env.example` lists knowledge vars; `infra/README.md` + root README start order
- [x] Optional `infra/kb-pipeline/` Dockerfile + docs (host CLIs remain default)
- [x] `DECISIONS.md` records knowledge IaC = Phase 1.5
- [x] App supports `CHROMA_HOST` / `CHROMA_PORT`; tests cover layout + env helper

### Decision table (Phase 1.5 → next)

| Observation | Action |
|-------------|--------|
| Neo4j healthy | Phase 4 uses `--require-neo4j` for live gate |
| Chroma healthy + `CHROMA_HOST` set | Phase 4 `build_kb` targets server |
| Docker unavailable | Offline fallback; do not block file work |
| Agents need KB | Same Compose project/env as Phase 4 load |

## Phase 1.5 status

**Complete** (Compose units + env contract + Chroma server client). Live load demos: start `infra/compose.yml`, then Phase 4 CLIs. See [`04-stores.md`](04-stores.md) and [`06-ops-and-acceptance.md`](06-ops-and-acceptance.md).
