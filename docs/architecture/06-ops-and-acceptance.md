# Architecture — Phase 6: Ops, deliverables, and remaining IaC

## Purpose

Ship assignment deliverables (README, samples, demo) and finish **non-knowledge** ops IaC (MCP, optional app, umbrella compose).

**Knowledge store IaC** (Neo4j, Chroma, optional `kb-pipeline`) is **Phase 1.5** — see [`01b-knowledge-infra.md`](01b-knowledge-infra.md). Phase 4 **loads** into that infra; Phase 5 agents **reuse** it. Do not re-introduce a second knowledge stack here.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Ops runbook | this doc + README | Full demo start order |
| Knowledge IaC | `infra/neo4j/`, `infra/chroma/`, optional `infra/kb-pipeline/` | **Phase 1.5 done** |
| MCP / app IaC | `infra/mcp-weather/`, `infra/mcp-currency/`, `infra/app/` | This phase (+ Phase 5 when servers exist) |
| Optional umbrella | `infra/compose.yml` | `include` / profiles for “full local” |
| Env contract | `.env.example` | Vars per unit |
| Acceptance checklist | below | Assignment deliverables 15–20 |

## Infrastructure as code (split ownership)

**Decision:** Docker Compose **per service** under `infra/`. Secrets stay in `.env`.

### Knowledge units (Phase 1.5 — implement early)

| Service | Unit | Used by |
|---------|------|---------|
| Neo4j | `infra/neo4j/` | Phase 4 load + Phase 5 agents (**done**) |
| Chroma | `infra/chroma/` | Phase 4 `build_kb` + Phase 5 retrieval (**done**) |
| KB pipeline job (optional) | `infra/kb-pipeline/` | Reproducible DE → load (**done**) |

### Runtime units (Phase 5–6)

| Service | Unit | Notes |
|---------|------|--------|
| MCP weather | `infra/mcp-weather/` | After Phase 5 weather server exists |
| MCP currency | `infra/mcp-currency/` | Independent of weather |
| Streamlit app | `infra/app/` or documented CLI | Optional container |
| LLM providers | `.env` only | Not local infra |

### Principles

1. **Separate stacks** — start only what you need.
2. **One knowledge path** — agents never point at a different Neo4j/Chroma than Phase 4 loaded.
3. **Offline fallback** — `--memory` / `--embeddings fake` for CI without Docker.
4. **Parity with `.env.example`**.

### Suggested start order (full local demo)

```text
1. infra/neo4j + infra/chroma     (Phase 1.5)
2. crawl → normalize → ontology   (or infra/kb-pipeline)
3. build_kb + load_neo4j          (Phase 4 → into infra)
4. infra/mcp-weather + mcp-currency
5. Streamlit / infra/app
6. tests/use_cases suite
```

### Exit criteria (Phase 6 slice)

- [ ] MCP + optional app Compose documented (knowledge units already done in 1.5)
- [ ] Optional umbrella compose with `profiles` or `include`
- [ ] README full demo path; no secrets in git
- [ ] Acceptance deliverables 15–20 checked

## Ops runbook (to be filled)

1. Start knowledge infra (1.5)  
2. Re-run crawl / normalize / ontology if sources change  
3. Rebuild Chroma + load Neo4j (Phase 4 into same infra)  
4. Start MCP servers  
5. Run Streamlit  
6. Run use-case suite  

## Acceptance checklist (assignment)

Mirror [`00-overview.md`](00-overview.md) acceptance criteria and map to `docs/USE_CASES.md`. Deliverables: polished README, sample Q&A, short demo notes.

## Phase 6 status

**Planned.** Knowledge IaC is Phase 1.5; this phase focuses on deliverables + MCP/app/umbrella after Phase 5 use-case pass.
