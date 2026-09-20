# Phase 1.5 — Knowledge infrastructure

Composable Docker Compose units for Neo4j and Chroma. Phase 4 **loads** into these stores; Phase 5 agents **reuse** the same endpoints.

## Quick start (repo root)

```bash
cp .env.example .env
# set NEO4J_PASSWORD=changeme (or another password)

# Both stores
docker compose -f infra/compose.yml up -d

# Or separately
docker compose -f infra/neo4j/compose.yml up -d
docker compose -f infra/chroma/compose.yml up -d
```

Wait for healthy, then from the host (with `.env` loaded):

```bash
# Point app at Compose Chroma (optional; omit for local data/chroma/)
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export NEO4J_PASSWORD=changeme

python scripts/build_kb.py --embeddings fake --gate
python scripts/load_neo4j.py --require-neo4j
```

## Units

| Path | Service | Host ports |
|------|---------|------------|
| `neo4j/` | Neo4j 5 | 7474 HTTP, 7687 Bolt |
| `chroma/` | Chroma 0.5 | 8000 |
| `kb-pipeline/` | Optional job image | — (profile `pipeline`) |
| `compose.yml` | Umbrella include | both |

## Networks for kb-pipeline

Use the umbrella profile (shared Compose network):

```bash
docker compose -f infra/compose.yml up -d
docker compose -f infra/compose.yml --profile pipeline run --rm kb-pipeline \
  python scripts/build_kb.py --embeddings fake
```

**Host CLIs are the default** for Phase 2–4; `kb-pipeline` is optional.

## Tear down

```bash
docker compose -f infra/compose.yml down
# add -v to wipe Neo4j/Chroma volumes
```

## Offline (no Docker)

Leave `CHROMA_HOST` unset (`CHROMA_PATH=data/chroma`) and use `python scripts/load_neo4j.py --memory`.
