# Architecture — Phase 6: Ops, deliverables, and remaining IaC

## Purpose

Ship assignment deliverables (README, samples, demo) and finish **non-knowledge** ops IaC (MCP, optional app, umbrella compose).

**Knowledge store IaC** (Neo4j, Chroma, optional `kb-pipeline`) is **Phase 1.5** — see [`01b-knowledge-infra.md`](01b-knowledge-infra.md). Phase 4 **loads** into that infra; Phase 5 agents **reuse** it. Do not re-introduce a second knowledge stack here.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Ops runbook | this doc + [`infra/README.md`](../../infra/README.md) | Full demo start order |
| Knowledge IaC | `infra/neo4j/`, `infra/chroma/`, optional `infra/kb-pipeline/` | **Phase 1.5 done** |
| MCP IaC | `infra/mcp-weather/`, `infra/mcp-currency/` | Profile `mcp` |
| App IaC | `infra/app/` | Profile `app` (optional; host Streamlit preferred) |
| Umbrella | `infra/compose.yml` | `include` + profiles `pipeline` / `mcp` / `app` |
| Env contract | `.env.example` | Vars per unit |
| Demo | [`DEMO_CHECKLIST.md`](../DEMO_CHECKLIST.md), [`SAMPLE_QA.md`](../SAMPLE_QA.md) | Grader / live demo |
| Acceptance | below + [`USE_CASES.md`](../USE_CASES.md) | Assignment criteria |

## Infrastructure as code (split ownership)

**Decision:** Docker Compose **per service** under `infra/`. Secrets stay in `.env`.

### Knowledge units (Phase 1.5 — done)

| Service | Unit | Used by |
|---------|------|---------|
| Neo4j | `infra/neo4j/` | Phase 4 load + Phase 5 agents |
| Chroma | `infra/chroma/` | Phase 4 `build_kb` + Phase 5 retrieval |
| KB pipeline job | `infra/kb-pipeline/` | Optional DE → load |

### Runtime units (Phase 6 — done)

| Service | Unit | Notes |
|---------|------|--------|
| MCP weather | `infra/mcp-weather/` | Profile `mcp`; stdio CMD or health sidecar |
| MCP currency | `infra/mcp-currency/` | Independent of weather |
| Streamlit app | `infra/app/` | Profile `app`; mounts `data/` + `ontology/` |
| LLM providers | `.env` only | Not local infra |

### Principles

1. **Separate stacks** — start only what you need (`up -d` vs `--profile mcp` / `app`).
2. **One knowledge path** — agents never point at a different Neo4j/Chroma than Phase 4 loaded.
3. **Offline fallback** — `--memory` / `--embeddings fake` / `MCP_MOCK_MODE=true` for CI without Docker.
4. **Parity with `.env.example`**.
5. **In-process MCP clients** remain the default for agents; Compose MCP units provide ops/stdio parity.

### Suggested start order (full local demo)

```text
1. infra/neo4j + infra/chroma     (Phase 1.5)
2. crawl → normalize → ontology   (or --profile pipeline)
3. build_kb + load_neo4j          (Phase 4 → into infra)
4. optional --profile mcp
5. Streamlit host or --profile app
6. pytest tests/use_cases/
```

```bash
export NEO4J_PASSWORD=changeme
docker compose -f infra/compose.yml up -d
export CHROMA_HOST=localhost CHROMA_PORT=8000
python scripts/build_kb.py --embeddings fake --gate
python scripts/load_neo4j.py --require-neo4j
docker compose -f infra/compose.yml --profile mcp --profile app up -d --build
# or: streamlit run app/streamlit_app.py
pytest tests/use_cases/ -q
```

### Exit criteria (Phase 6)

- [x] MCP + optional app Compose documented (knowledge units already done in 1.5)
- [x] Umbrella compose with `profiles` (`pipeline`, `mcp`, `app`) + `include`
- [x] README full demo path; no secrets in git
- [x] Acceptance deliverables checked (below)
- [x] `DEMO_CHECKLIST.md` + `SAMPLE_QA.md`
- [x] `tests/test_phase6_ops.py` layout/env contract

## Ops runbook

1. Start knowledge infra (`docker compose -f infra/compose.yml up -d`)  
2. Re-run crawl / normalize / ontology if sources change  
3. Rebuild Chroma + load Neo4j into the **same** infra  
4. Optional: `--profile mcp` for weather/currency containers  
5. Run Streamlit (host or `--profile app`)  
6. Run `pytest tests/use_cases/ -q`  
7. Tear down with `down` (add `-v` to wipe volumes)

### MCP mock vs live

| Mode | When | Behavior |
|------|------|----------|
| `MCP_MOCK_MODE=true` | Offline demos / CI | Documented mock weather + FX |
| `MCP_MOCK_MODE=false` | Live demo | Open-Meteo + Frankfurter |
| Tool failure | Network / force-fail | Explicit `[Error]`; **no** fabricated temps/rates |

## Acceptance checklist (assignment)

| Criterion | Evidence |
|-----------|----------|
| KB from ≥3 travel resources | `data/sources.yaml` (4 sources); Phase 1–2 |
| Embedding-based semantic retrieval | Chroma + `HybridRetriever`; Phase 4 |
| Grounded answers with source references | `[KB fact]` + citations; UC-RAG-* |
| Weather via MCP | `mcp_servers/weather`; UC-WX-* |
| Currency via MCP | `mcp_servers/currency`; UC-FX-* |
| ≥1 combined RAG + MCP | UC-COMBO-01 |
| Multi-turn context | SessionState; UC-MEM-* |
| Intent-based tool selection | A0 router; UC-ROUTE-* |
| Missing KB / tool failures | UC-NEG-*, UC-WX-05, UC-FX-04 |
| Simple usable UI | `app/streamlit_app.py` |

Deliverables: polished [`README.md`](../../README.md), [`SAMPLE_QA.md`](../SAMPLE_QA.md), [`DEMO_CHECKLIST.md`](../DEMO_CHECKLIST.md).

## Phase 6 status

**Complete.** Knowledge IaC remains Phase 1.5; this phase added MCP/app Compose profiles, umbrella includes, demo docs, and acceptance mapping. Pipeline is feature-complete for the assignment gate.
