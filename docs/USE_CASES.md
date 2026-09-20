# Use cases — AI Travel Planning Assistant

Pass/fail filled during Phase 5. Skeleton created in Phase 0.

**Pass bar (Phase 5 gate):** UC-COMBO-01, all UC-ROUTE-*, all UC-NEG-*, UC-LLM-01..04, plus ≥4 RAG, ≥2 WX, ≥2 FX, ≥2 MEM green.

Legend: `pending` | `pass` | `fail` | `blocked`

---

## UC-RAG — Destination knowledge (RAG only)

| ID | User query | Expected | Status |
|----|------------|----------|--------|
| UC-RAG-01 | What are the must-visit attractions in Singapore? | Grounded list + ≥1 citation; no MCP | pending |
| UC-RAG-02 | Which neighbourhoods are suitable for cultural experiences? | Districts from KB + citations | pending |
| UC-RAG-03 | How can a tourist travel around Singapore? | Transport guidance + citations | pending |
| UC-RAG-04 | Suggest activities for a family with children | Family-tagged activities; preference stored | pending |
| UC-RAG-05 | Create a three-day sightseeing itinerary | Day-wise from KB; facts vs suggestions labeled | pending |
| UC-RAG-06 | What indoor attractions can I visit? | Indoor-tagged only; citations | pending |
| UC-RAG-07 | What is the best nightlife in Antarctica? | Clear KB insufficiency; no invention | pending |

---

## UC-WX — Weather MCP

| ID | User query | Expected | Status |
|----|------------|----------|--------|
| UC-WX-01 | What is the weather in Singapore? | MCP current; MCP badge | pending |
| UC-WX-02 | What is the forecast for the next three days? | Day-wise forecast from MCP | pending |
| UC-WX-03 | Is rain expected during my trip? | Answer grounded in MCP forecast | pending |
| UC-WX-04 | Should I plan indoor or outdoor activities tomorrow? | MCP + suggestion label | pending |
| UC-WX-05 | (MCP down) weather question | Explicit failure; no fake temperatures | pending |

---

## UC-FX — Currency MCP

| ID | User query | Expected | Status |
|----|------------|----------|--------|
| UC-FX-01 | Convert INR 50,000 to SGD | Amount + MCP rate | pending |
| UC-FX-02 | How much is 200 SGD in INR? | Reverse conversion | pending |
| UC-FX-03 | Convert my travel budget from USD to Singapore dollars | Ask amount if missing OR use state | pending |
| UC-FX-04 | (MCP down) convert INR to SGD | Explicit failure; no fake rate | pending |

---

## UC-COMBO — Combined RAG + MCP

| ID | User query | Expected | Status |
|----|------------|----------|--------|
| UC-COMBO-01 | Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast | **Required:** RAG + weather MCP + day-wise + indoor alternatives + KB/MCP/LLM labels | pending |
| UC-COMBO-02 | I have a budget of INR 60,000. Convert it to SGD and suggest a three-day itinerary | Currency MCP + RAG itinerary + labels | pending |
| UC-COMBO-03 | Suggest outdoor attractions and replace them with indoor options if rain is expected | RAG outdoor/indoor + weather MCP | pending |
| UC-COMBO-04 | Plan a family trip and include the latest weather forecast | Family preference + weather | pending |
| UC-COMBO-05 | Create a cultural itinerary and show my budget in the destination currency | Culture RAG + FX MCP | pending |

---

## UC-ROUTE — Intent / tool selection

| ID | Scenario | Expected intent | Status |
|----|----------|-----------------|--------|
| UC-ROUTE-01 | Attractions only | `rag_only` — no MCP | pending |
| UC-ROUTE-02 | Weather only | `weather_only` | pending |
| UC-ROUTE-03 | Convert only | `currency_only` | pending |
| UC-ROUTE-04 | Itinerary + weather | `combined_itinerary` | pending |
| UC-ROUTE-05 | Book me a hotel | `out_of_scope` | pending |

---

## UC-MEM — Multi-turn context

| ID | Turn sequence | Expected | Status |
|----|---------------|----------|--------|
| UC-MEM-01 | “We are a family of 4” → “Suggest activities” | Family-appropriate without re-asking | pending |
| UC-MEM-02 | “Budget INR 60,000” → “Show my budget in SGD” | Uses stored amount | pending |
| UC-MEM-03 | Prefer indoor → later itinerary | Biases indoor options | pending |

---

## UC-LLM — Provider toggle (openai | gemini | cursor)

| ID | Scenario | Expected | Status |
|----|----------|----------|--------|
| UC-LLM-01 | Sidebar/env = OpenAI; ask RAG question | Answer via OpenAI; log `provider=openai` | pending |
| UC-LLM-02 | Toggle to Gemini; same style question | Answer via Gemini; log `provider_changed` then `gemini` | pending |
| UC-LLM-03 | Toggle to Cursor with valid base URL + key | Answer via Cursor-compatible client; log `provider=cursor` | pending |
| UC-LLM-04 | Selected provider missing API key | User-visible config error; no silent fallback; no fabricated answer | pending |

---

## UC-NEG — Failure / grounding

| ID | Scenario | Expected | Status |
|----|----------|----------|--------|
| UC-NEG-01 | Empty retrieval | Honest gap statement | pending |
| UC-NEG-02 | Weather MCP timeout | No fabricated forecast | pending |
| UC-NEG-03 | Currency MCP 500 | No fabricated rate | pending |
| UC-NEG-04 | Ask MCP for “best temples in Chinatown” | Router sends to RAG, not MCP | pending |

---

## Run notes

- Automated / semi-auto runners: `tests/use_cases/` (Phase 5)
- Demo checklist: `docs/DEMO_CHECKLIST.md` (Phase 6)
