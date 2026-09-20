# Optional KB pipeline image

Dockerfile builds a Python image with `src/`, `scripts/`, and seed data for one-shot loads.

**Default workflow:** run CLIs on the host against Compose Neo4j/Chroma (see [`../README.md`](../README.md)).

**Containerized run** (shared network via umbrella):

```bash
export NEO4J_PASSWORD=changeme
docker compose -f infra/compose.yml up -d
docker compose -f infra/compose.yml --profile pipeline run --rm kb-pipeline \
  python scripts/build_kb.py --embeddings fake
docker compose -f infra/compose.yml --profile pipeline run --rm kb-pipeline \
  python scripts/load_neo4j.py --require-neo4j
```

Inside the job container: `NEO4J_URI=bolt://neo4j:7687`, `CHROMA_HOST=chroma`.
