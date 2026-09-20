# Sample Q&A — Singapore Travel Assistant

Expected shapes for demos and graders. Live wording varies by LLM provider; **labels and grounding** should match.

---

### 1. RAG only — attractions

**User:** What are the must-visit attractions in Singapore?

**Expect:**
- Intent `rag_only` (no MCP)
- `[KB fact]` — natural chat-style answer grounded in KB, with ≥1 citation (title + URL)
- Optional `[LLM suggestion]` (e.g. itinerary shaping); not a second paste of raw chunks

---

### 2. Weather MCP

**User:** What is the forecast for the next three days?

**Expect:**
- Intent `weather_only`
- `[MCP data]` with day-wise temps / precip (live Open-Meteo or mock)
- Never invent °C if MCP fails — `[Error]` instead

---

### 3. Currency MCP

**User:** Convert INR 50000 to SGD

**Expect:**
- Intent `currency_only`
- `[MCP data]` with amount, rate, converted SGD

---

### 4. Combined (required) — weather-aware itinerary

**User:** Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast

**Expect:**
- Intent `combined_itinerary`
- `[KB fact]` + citations  
- `[MCP data]` forecast  
- `[LLM suggestion]` day-wise plan; indoor bias on rainy days  

---

### 5. Multi-turn memory

**User:** We are a family of 4  
**User:** Suggest activities  

**Expect:** Session keeps `traveler_type=family`; activities stay grounded in KB without re-asking party size.

---

### 6. Out of scope

**User:** Book me a hotel in Marina Bay

**Expect:** Clear out-of-scope message; no fake booking.

---

### 7. LLM config error

**Setup:** `LLM_PROVIDER=openai` with empty `OPENAI_API_KEY`

**User:** What are attractions in Singapore?

**Expect:** User-visible configuration error; **no** silent fallback to another provider.
