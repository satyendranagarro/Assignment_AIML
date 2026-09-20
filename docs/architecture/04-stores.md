# Architecture — Phase 4: Chroma + Neo4j stores

## Purpose

Index normalized Singapore KB text into **Chroma** (vector) and load the Phase 3 ontology into **Neo4j** (or in-memory graph for offline smoke), then expose a **HybridRetriever** for Phase 5 agents.

Phase 3 decision: dense typed entities + relations → **hybrid** (Chroma primary + graph expansion).

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Processed docs | `data/processed/**/*.json` | Chunk + embed source |
| Entities | `ontology/entities.json` | Graph nodes/edges + chunk entity tags |
| Chroma | `data/chroma/` | Persistent vector collection `singapore_kb` |
| Graph | Neo4j (`NEO4J_*`) or in-memory | Entity / relation expansion |
| Library | `src/rag/`, `src/graph/`, `src/llm/`, `src/observability/` | Build + retrieve + logging |
| CLIs | `scripts/build_kb.py`, `load_neo4j.py`, `eval_retrieval.py` | Index, load, smoke |

## Pipeline

```text
data/processed/*.json
        │
        ▼
   chunk (≈800 chars, overlap 120) ── citation metadata (title/url/source_id/doc_id)
        │                              + entity_ids from ontology evidence
        ▼
   embed via src/llm/factory.get_embeddings()
        │
        ▼
   Chroma (data/chroma/)
        │
ontology/entities.json ──► Neo4j KBEntity/REL  (or InMemoryGraphStore)
        │
        └─ HybridRetriever: similarity_search + name/alias graph expand
```

### Chunk contract

Each chunk stores: `chunk_id`, `doc_id`, `source_id`, `title`, `url`, `topics`, `entity_ids`, `chunk_index`.

Agents must cite `title` + `url` from retrieved chroma hits. Never invent destination facts.

### Embeddings

| Provider | Env | Notes |
|----------|-----|-------|
| `openai` | `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL` | Default production |
| `gemini` | `GOOGLE_API_KEY` | Optional |
| `cursor` | `CURSOR_API_KEY` + `CURSOR_LLM_BASE_URL` | OpenAI-compatible |
| `fake` | — | Lexical hash vectors for offline smoke/tests |

`EMBEDDING_PROVIDER` overrides chat provider. Missing key → `ConfigError` (no silent fallback). Re-index Chroma after changing embedding provider.

### Graph model

- Nodes: `KBEntity` (`id`, `name`, `class`, `aliases`, `tags`)
- Edges: `REL {type}` (`located_in`, `nearby`, `part_of_itinerary`, …)
- Evidence: `KBDoc` via `EVIDENCED_IN`

If `NEO4J_PASSWORD` is unset or Neo4j is down, `open_graph_store()` uses **InMemoryGraphStore** so local smoke still passes. Use `scripts/load_neo4j.py --require-neo4j` for a hard check.

### Observability

`retrieve.start` / `retrieve.end` / `retrieve.index` / `retrieve.error` via `src/observability` with `correlation_id`, `llm_provider`, truncated `query_preview`.

## How to run

```bash
# Ensure processed docs + ontology exist
python scripts/crawl.py --force-manual
python scripts/normalize.py
python scripts/build_ontology.py

# Offline smoke (no API key / no Neo4j)
python scripts/build_kb.py --embeddings fake --gate
python scripts/load_neo4j.py --memory
python scripts/eval_retrieval.py --embeddings fake --gate

# Production-ish (OpenAI embeddings + Neo4j)
export OPENAI_API_KEY=...
export NEO4J_PASSWORD=...
python scripts/build_kb.py --embeddings openai
python scripts/load_neo4j.py --require-neo4j
python scripts/eval_retrieval.py --embeddings openai

pytest tests/test_phase4_stores.py -q
```

## Exit criteria (gate → Phase 5)

- [x] Chunks preserve citation metadata (title + url)
- [x] Chroma indexed with ≥5 chunks; smoke queries return hits
- [x] Graph loads ≥20 entities and ≥5 relations (Neo4j or memory)
- [x] HybridRetriever merges vector + graph hits
- [x] LLM/embedding factory + structured retrieve logs wired
- [x] Tests cover chunk, build, graph expand, gate, CLI

### Decision table (Phase 4 → 5)

| Observation | Action in Phase 5 |
|-------------|-------------------|
| Graph expansions add useful neighbors | Keep **hybrid** retrieval in A1/A4 |
| Graph noisy / weak name match | Chroma-only retrieve; keep graph for display |
| Bad chunks / weak overlap | Retune `chunk_size` / overlap; rebuild before agents |

## Phase 4 status

**Complete** when `python scripts/build_kb.py --embeddings fake --gate` exits 0 and `DECISIONS.md` records hybrid mode. Next: Phase 5 agents + MCP + UI (`05-agents.md`).
