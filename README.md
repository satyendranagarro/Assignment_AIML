# AI Travel Planning Assistant (Singapore)

Context-aware travel assistant: **RAG knowledge base** + **MCP weather/currency** + **combined itineraries**.

Assignment brief: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](Requirement/AI_Travel_Planning_Assistant_Assignment.pdf)

## Status

**Phase 5 agents done.** Next: Phase 6 deliverables + MCP/app Compose. See [`DECISIONS.md`](DECISIONS.md).

| Phase | Status |
|-------|--------|
| 0 Skill + scaffold | done |
| 1 Data pipeline | done |
| 1.5 Knowledge IaC (Neo4j + Chroma) | done |
| 2 Crawl | done |
| 3 Ontology | done |
| 4 Load KB into infra | done |
| 5 Agents + MCP + UI | done |
| 6 Deliverables + runtime IaC | pending |

## Architecture

Start here: [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md)

Knowledge infra: [`infra/README.md`](infra/README.md) · [`docs/architecture/01b-knowledge-infra.md`](docs/architecture/01b-knowledge-infra.md)

Ops / MCP–app IaC (Phase 6): [`docs/architecture/06-ops-and-acceptance.md`](docs/architecture/06-ops-and-acceptance.md)

Use cases: [`docs/USE_CASES.md`](docs/USE_CASES.md)

Agent workflow skill: [`.cursor/skills/travel-assistant-pipeline/SKILL.md`](.cursor/skills/travel-assistant-pipeline/SKILL.md)

## Stack (A)

LangChain · OpenAI / Gemini / Cursor · Chroma · Neo4j · Streamlit · MCP (weather + currency)

**Infra:** `infra/neo4j` + `infra/chroma` (Phase 1.5). Agents reuse the same stores. Phase 5–6 adds MCP/app.

## Setup

Requires **Python 3.10+** (3.12 recommended; `mcp` package).

1. Copy `.env.example` → `.env` and set keys (`NEO4J_PASSWORD=changeme` for local Compose)  
2. `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`  
3. Start knowledge infra: `docker compose -f infra/compose.yml up -d`  
4. Optional live Chroma server: `export CHROMA_HOST=localhost CHROMA_PORT=8000` (omit for local `data/chroma/`)  
5. `python scripts/crawl.py --force-manual --update-matrix`  
6. `python scripts/build_ontology.py`  
7. `python scripts/build_kb.py --embeddings fake --gate`  
8. `python scripts/load_neo4j.py --require-neo4j` (or `--memory` offline)  
9. Agents UI: `export LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake MCP_MOCK_MODE=true && streamlit run app/streamlit_app.py`  
10. Use cases: `pytest tests/test_phase5_agents.py tests/use_cases/ -q`  

Phase 5 architecture: [`docs/architecture/05-agents.md`](docs/architecture/05-agents.md)

## Out of scope

Booking, payments, navigation, reservations.
