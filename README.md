# AI Travel Planning Assistant (Singapore)

Context-aware travel assistant: **RAG knowledge base** + **MCP weather/currency** + **combined itineraries**.

Assignment brief: [`Requirement/AI_Travel_Planning_Assistant_Assignment.pdf`](Requirement/AI_Travel_Planning_Assistant_Assignment.pdf)

## Status

**All phases complete (0 → 6).** See [`DECISIONS.md`](DECISIONS.md).

| Phase | Status |
|-------|--------|
| 0 Skill + scaffold | done |
| 1 Data pipeline | done |
| 1.5 Knowledge IaC (Neo4j + Chroma) | done |
| 2 Crawl | done |
| 3 Ontology | done |
| 4 Load KB into infra | done |
| 5 Agents + MCP + UI | done |
| 6 Deliverables + runtime IaC | done |

## Architecture

| Doc | Content |
|-----|---------|
| [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md) | System context |
| [`docs/architecture/05-agents.md`](docs/architecture/05-agents.md) | Agents A0–A4 |
| [`docs/architecture/06-ops-and-acceptance.md`](docs/architecture/06-ops-and-acceptance.md) | Ops + acceptance |
| [`infra/README.md`](infra/README.md) | Compose units (knowledge + MCP + app) |
| [`docs/USE_CASES.md`](docs/USE_CASES.md) | Use-case pass bar |
| [`docs/SAMPLE_QA.md`](docs/SAMPLE_QA.md) | Sample prompts / expected labels |
| [`docs/DEMO_CHECKLIST.md`](docs/DEMO_CHECKLIST.md) | Live / offline demo steps |

## Stack (A)

LangChain · OpenAI / Gemini / Cursor · Chroma · Neo4j · Streamlit · MCP (weather + currency)

Agents reuse the **same** Neo4j/Chroma that Phase 4 loads (Phase 1.5 Compose).

## Quick start

Requires **Python 3.10+** (3.12 recommended). Set a real provider key in `.env` (see `.env.example`).

```bash
cp .env.example .env
# Set OPENAI_API_KEY (or GOOGLE_API_KEY / CURSOR_API_KEY / Ollama) and LLM_PROVIDER
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Index KB (if data/chroma empty)
python scripts/crawl.py --force-manual
python scripts/normalize.py
python scripts/build_ontology.py
python scripts/build_kb.py --embeddings openai --gate
python scripts/load_neo4j.py --memory

streamlit run app/streamlit_app.py
```

Try prompts in [`docs/SAMPLE_QA.md`](docs/SAMPLE_QA.md). Checklist: [`docs/DEMO_CHECKLIST.md`](docs/DEMO_CHECKLIST.md).

```bash
pytest tests/ -q
```

## Full local demo (Compose)

```bash
# 1. Knowledge stores
export NEO4J_PASSWORD=changeme
docker compose -f infra/compose.yml up -d

# 2. Load into the same infra
export CHROMA_HOST=localhost CHROMA_PORT=8000
python scripts/build_kb.py --embeddings openai --gate
python scripts/load_neo4j.py --require-neo4j

# 3. Optional MCP sidecars + Streamlit container
docker compose -f infra/compose.yml --profile mcp --profile app up -d --build
# UI: http://localhost:8501
# Or on host: streamlit run app/streamlit_app.py
```

Profiles: `pipeline` (kb job) · `mcp` (weather/currency) · `app` (Streamlit).

## MCP notes

- Agents use **in-process** Open-Meteo / Frankfurter clients by default.
- MCP down → explicit error; **no** fabricated temperatures or FX rates.
- Stdio servers: `python -m mcp_servers.weather.server` / `currency.server`.

## LLM toggle

`LLM_PROVIDER=openai|gemini|cursor|ollama` (Streamlit sidebar overrides). Missing key → config error; no silent fallback. See `.env.example`.

## Out of scope

Booking, payments, navigation, reservations.
