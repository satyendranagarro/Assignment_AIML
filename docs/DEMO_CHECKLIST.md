# Demo checklist — AI Travel Planning Assistant

Short path for a live or offline demo. Full ops: [`docs/architecture/06-ops-and-acceptance.md`](architecture/06-ops-and-acceptance.md).

## A. Offline demo (no Docker / no API keys) — ~5 min

- [ ] `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- [ ] KB already built under `data/chroma/` **or** run `python scripts/build_kb.py --embeddings fake --gate`
- [ ] `export LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake MCP_MOCK_MODE=true`
- [ ] `streamlit run app/streamlit_app.py`
- [ ] Run sample prompts from [`SAMPLE_QA.md`](SAMPLE_QA.md) (at least UC-COMBO-01)
- [ ] `pytest tests/use_cases/ -q` → green

## B. Full local demo (Compose knowledge + live tools) — ~15 min

- [ ] Copy `.env.example` → `.env`; set `NEO4J_PASSWORD`, optional `OPENAI_API_KEY`
- [ ] `docker compose -f infra/compose.yml up -d` (Neo4j + Chroma healthy)
- [ ] `export CHROMA_HOST=localhost CHROMA_PORT=8000`
- [ ] `python scripts/crawl.py --force-manual && python scripts/normalize.py && python scripts/build_ontology.py`
- [ ] `python scripts/build_kb.py --embeddings openai --gate` (or `fake`)
- [ ] `python scripts/load_neo4j.py --require-neo4j`
- [ ] Optional: `docker compose -f infra/compose.yml --profile mcp up -d --build`
- [ ] `export LLM_PROVIDER=openai MCP_MOCK_MODE=false` (or keep mock)
- [ ] `streamlit run app/streamlit_app.py` — toggle provider in sidebar
- [ ] Show labels: `[KB fact]`, `[MCP data]`, `[LLM suggestion]`
- [ ] Show MCP failure path: stop network / set force-fail story via `MCP_MOCK_MODE` docs

## C. Talking points (assignment)

1. ≥3 Singapore sources → Chroma citations + Neo4j expand (hybrid)  
2. Intent router picks RAG / weather / FX / combined without LLM  
3. Combined weather-aware 3-day itinerary (UC-COMBO-01)  
4. Multi-turn memory (family / budget / indoor)  
5. No fabricated weather or FX when MCP is down  

## D. Tear down

```bash
docker compose -f infra/compose.yml --profile mcp --profile app down
```
