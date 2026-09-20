# AI Travel Planning Assistant (Singapore)

Context-aware travel assistant: **RAG knowledge base** + **MCP weather/currency** + **combined itineraries**.

Assignment brief: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](Requirement/AI_Travel_Planning_Assistant_Assignment.pdf)

## Status

**Phase 4 complete (Chroma + hybrid GraphRAG).** Next: Phase 5 agents + MCP + UI. See [`DECISIONS.md`](DECISIONS.md).

| Phase | Status |
|-------|--------|
| 0 Skill + scaffold | done |
| 1 Data pipeline | done |
| 2 Crawl | done |
| 3 Ontology | done |
| 4 Chroma + Neo4j | done |
| 5 Agents + MCP + UI | pending |
| 6 Deliverables | pending |

## Architecture

Start here: [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md)

Use cases: [`docs/USE_CASES.md`](docs/USE_CASES.md)

Agent workflow skill: [`.cursor/skills/travel-assistant-pipeline/SKILL.md`](.cursor/skills/travel-assistant-pipeline/SKILL.md)

## Stack (A)

LangChain · OpenAI / Gemini / Cursor · Chroma · Neo4j · Streamlit · MCP (weather + currency)

## Setup

1. Copy `.env.example` → `.env` and set keys  
2. `pip install -r requirements.txt`  
3. `python scripts/crawl.py --force-manual --update-matrix` (or live crawl with manual fallback)  
4. `python scripts/build_ontology.py`  
5. `python scripts/build_kb.py --embeddings fake --gate` (use `openai` when `OPENAI_API_KEY` is set)  
6. `python scripts/load_neo4j.py` (needs Neo4j + `NEO4J_PASSWORD`, or `--memory`)  
7. Follow phase docs under `docs/architecture/`

## Out of scope

Booking, payments, navigation, reservations.
