# AI Travel Planning Assistant (Singapore)

Context-aware travel assistant: **RAG knowledge base** + **MCP weather/currency** + **combined itineraries**.

Assignment brief: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](Requirement/AI_Travel_Planning_Assistant_Assignment.pdf)

## Status

**Phase 4 complete (offline path).** Next: Phase **1.5 knowledge IaC** (backfill) + Phase 5 agents. See [`DECISIONS.md`](DECISIONS.md).

| Phase | Status |
|-------|--------|
| 0 Skill + scaffold | done |
| 1 Data pipeline | done |
| 1.5 Knowledge IaC (Neo4j + Chroma) | pending |
| 2 Crawl | done |
| 3 Ontology | done |
| 4 Load KB into infra | done (offline); live path needs 1.5 |
| 5 Agents + MCP + UI | pending |
| 6 Deliverables + runtime IaC | pending |

## Architecture

Start here: [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md)

Knowledge infra (Phase 1.5): [`docs/architecture/01b-knowledge-infra.md`](docs/architecture/01b-knowledge-infra.md)

Ops / MCP–app IaC (Phase 6): [`docs/architecture/06-ops-and-acceptance.md`](docs/architecture/06-ops-and-acceptance.md)

Use cases: [`docs/USE_CASES.md`](docs/USE_CASES.md)

Agent workflow skill: [`.cursor/skills/travel-assistant-pipeline/SKILL.md`](.cursor/skills/travel-assistant-pipeline/SKILL.md)

## Stack (A)

LangChain · OpenAI / Gemini / Cursor · Chroma · Neo4j · Streamlit · MCP (weather + currency)

**Infra:** Phase **1.5** Compose for Neo4j + Chroma (DE loads here; agents reuse). Phase **5–6** adds MCP/app. Start only what you need.

## Setup

1. Copy `.env.example` → `.env` and set keys  
2. `pip install -r requirements.txt`  
3. **(Phase 1.5)** Start knowledge infra when available: `infra/neo4j` + `infra/chroma`  
4. `python scripts/crawl.py --force-manual --update-matrix` (or live crawl with manual fallback)  
5. `python scripts/build_ontology.py`  
6. `python scripts/build_kb.py --embeddings fake --gate` (use `openai` when `OPENAI_API_KEY` is set)  
7. `python scripts/load_neo4j.py` (live: needs Neo4j + `NEO4J_PASSWORD`; offline: `--memory`)  
8. Follow phase docs under `docs/architecture/`

## Out of scope

Booking, payments, navigation, reservations.
