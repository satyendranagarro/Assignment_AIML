# AI Travel Planning Assistant (Singapore)

Context-aware travel assistant: **RAG knowledge base** + **MCP weather/currency** + **combined itineraries**.

Assignment brief: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](Requirement/AI_Travel_Planning_Assistant_Assignment.pdf)

## Status

**Phase 1 complete (source registry + coverage + ingest/normalize).** Next: Phase 2 crawl. See [`DECISIONS.md`](DECISIONS.md).

| Phase | Status |
|-------|--------|
| 0 Skill + scaffold | done |
| 1 Data pipeline | done |
| 2 Crawl | pending |
| 3 Ontology | pending |
| 4 Chroma + Neo4j | pending |
| 5 Agents + MCP + UI | pending |
| 6 Deliverables | pending |

## Architecture

Start here: [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md)

Use cases: [`docs/USE_CASES.md`](docs/USE_CASES.md)

Agent workflow skill: [`.cursor/skills/travel-assistant-pipeline/SKILL.md`](.cursor/skills/travel-assistant-pipeline/SKILL.md)

## Stack (A)

LangChain · OpenAI / Azure OpenAI · Chroma · Neo4j · Streamlit · MCP (weather + currency)

## Setup

1. Copy `.env.example` → `.env` and set keys  
2. `pip install -r requirements.txt`  
3. Neo4j running locally (Phase 4+)  
4. Follow phase docs under `docs/architecture/`

## Out of scope

Booking, payments, navigation, reservations.
