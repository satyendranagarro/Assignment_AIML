# Architecture — Phase 4: Load KB into knowledge infra

## Purpose

Index normalized Singapore KB text into **Chroma** and load the Phase 3 ontology into **Neo4j**, then expose a **HybridRetriever** for Phase 5 agents.

**Happy path:** Phase **1.5** infra (`infra/chroma/`, `infra/neo4j/`) is already up; this phase **loads** into those stores. Agents later use the **same** endpoints/volumes.

**Offline / CI fallback:** host-local `data/chroma/`, `--embeddings fake`, and `InMemoryGraphStore` (`--memory`) when Docker is unavailable.

Phase 3 decision: dense typed entities + relations → **hybrid** (Chroma primary + graph expansion).

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Processed docs | `data/processed/**/*.json` | Chunk + embed source |
| Entities | `ontology/entities.json` | Graph nodes/edges + chunk entity tags |
| Knowledge IaC | `infra/chroma/`, `infra/neo4j/` | Phase 1.5 — load targets |
| Chroma data | volume / `data/chroma/` | Persistent collection `singapore_kb` |
| Graph | Neo4j (`NEO4J_*`) or in-memory | Entity / relation expansion |
| Library | `src/rag/`, `src/graph/`, `src/llm/`, `src/observability/` | Build + retrieve + logging |
| CLIs | `scripts/build_kb.py`, `load_neo4j.py`, `eval_retrieval.py` | Index, load, smoke |

## Pipeline

```text
Phase 1.5: infra/chroma + infra/neo4j (up)
        │
data/processed/*.json
        │
        ▼
   chunk (≈800 chars, overlap 120) ── citation metadata (title/url/source_id/doc_id)
        │                              + entity_ids from ontology evidence
        ▼
   embed via src/llm/factory.get_embeddings()
        │
        ▼
   Chroma (infra/chroma or data/chroma/)
        │
ontology/entities.json ──► Neo4j (infra/neo4j)  [or InMemoryGraphStore offline]
        │
        └─ HybridRetriever: similarity_search + name/alias graph expand
              ▲
Phase 5 agents consume the same stores
```

### Chunk contract

Each chunk stores: `chunk_id`, `doc_id`, `source_id`, `title`, `url`, `topics`, `entity_ids`, `chunk_index`.

Agents must cite `title` + `url` from retrieved chroma hits. Never invent destination facts.

### Embeddings

| Provider | Env | Notes |
|----------|-----|-------|
| `openai` | `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL` | Default production |
| `gemini` | `GOOGLE_API_KEY`, `GEMINI_EMBEDDING_MODEL` | Optional |
| `ollama` | `OLLAMA_BASE_URL`, `OLLAMA_EMBEDDING_MODEL` | Local (`nomic-embed-text`) |
| `cursor` | `CursorAdapter` — `CURSOR_API_KEY` + `CURSOR_LLM_BASE_URL` | OpenAI-compatible gateway |
| `fake` | — | Lexical hash vectors for offline smoke/tests |

`EMBEDDING_PROVIDER` overrides chat provider. Missing key → `ConfigError` (no silent fallback). Re-index Chroma after changing embedding provider.

### Graph model

- Nodes: `KBEntity` (`id`, `name`, `class`, `aliases`, `tags`)
- Edges: `REL {type}` (`located_in`, `nearby`, `part_of_itinerary`, …)
- Evidence: `KBDoc` via `EVIDENCED_IN`

If `NEO4J_PASSWORD` is unset or Neo4j is down, `open_graph_store()` uses **InMemoryGraphStore** so local smoke still passes. Use `scripts/load_neo4j.py --require-neo4j` for the **live infra** gate (Phase 1.5 must be up).

### Observability

`retrieve.start` / `retrieve.end` / `retrieve.index` / `retrieve.error` via `src/observability` with `correlation_id`, `llm_provider`, truncated `query_preview`.

## How to run

```bash
# Phase 1.5 knowledge infra (when implemented)
docker compose -f infra/neo4j/compose.yml up -d
docker compose -f infra/chroma/compose.yml up -d

# Ensure processed docs + ontology exist
python scripts/crawl.py --force-manual
python scripts/normalize.py
python scripts/build_ontology.py

# Live path (preferred for demos / agent prep)
export NEO4J_PASSWORD=...
python scripts/build_kb.py --embeddings openai   # or fake against chroma volume
python scripts/load_neo4j.py --require-neo4j
python scripts/eval_retrieval.py --embeddings openai --gate

# Offline smoke (no Docker / no API key)
python scripts/build_kb.py --embeddings fake --gate
python scripts/load_neo4j.py --memory
python scripts/eval_retrieval.py --embeddings fake --gate

pytest tests/test_phase4_stores.py -q
```

## Exit criteria (gate → Phase 5)

- [x] Chunks preserve citation metadata (title + url)
- [x] Chroma indexed with ≥5 chunks; smoke queries return hits
- [x] Graph loads ≥20 entities and ≥5 relations (Neo4j or memory)
- [x] HybridRetriever merges vector + graph hits
- [x] LLM/embedding factory + structured retrieve logs wired
- [x] Tests cover chunk, build, graph expand, gate, CLI
- [x] **Live infra path:** Phase 1.5 Compose; set `CHROMA_HOST` + `load_neo4j.py --require-neo4j` for demos (offline fallback remains for CI)

### Decision table (Phase 4 → 5)

| Observation | Action in Phase 5 |
|-------------|-------------------|
| Graph expansions add useful neighbors | Keep **hybrid** retrieval in A1/A4 |
| Graph noisy / weak name match | Chroma-only retrieve; keep graph for display |
| Bad chunks / weak overlap | Retune `chunk_size` / overlap; rebuild before agents |
| Live stores loaded | Agents use **same** `NEO4J_*` / Chroma as this phase |

## Phase 4 status

**Complete.** Offline CI path (`--embeddings fake` / `--memory`) and live path via Phase 1.5 ([`01b-knowledge-infra.md`](01b-knowledge-infra.md), [`infra/README.md`](../../infra/README.md)). Next: Phase 5 agents on the same stack (`05-agents.md`).
