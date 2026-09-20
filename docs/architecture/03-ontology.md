# Architecture — Phase 3: Ontology / taxonomy

## Purpose

Turn normalized Singapore KB text into a **typed entity graph seed**: classes, tags, relations, and ≥20 **spot-checked** entities with citation evidence for Phase 4 Neo4j (+ optional GraphRAG).

Phase 2 decision: dumps contain clear place / district / transport names → **full ontology** (not light tags only).

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Taxonomy | `ontology/taxonomy.yaml` | Classes, relations, tags, merge aliases |
| JSON Schema | `ontology/schema.json` | Entity document contract |
| Gazetteer | `ontology/gazetteer.yaml` | Canonical seeds attested in KB text |
| Entities | `ontology/entities.json` | Extracted + spot-checked graph seed |
| Library | `src/ontology/` | Load, extract, validate, gate |
| CLI | `scripts/build_ontology.py` | Rebuild entities + Phase 3 gate |

## Model

**Classes:** `Attraction` · `District` · `ItineraryDay` · `TransportMode` · `Tip`

**Relations:** `located_in` · `suitable_for` · `nearby` · `part_of_itinerary`

**Tags:** `indoor` · `outdoor` · `family` · `culture` · `food` · `transport`

```text
data/processed/**/*.json
        │
        ▼
 gazetteer match ──► evidence snippets (title/url via doc)
        │
        ▼
 ontology/entities.json  ──spot-check≥20──► Phase 3 gate
        │
        └─ Phase 4: load_neo4j.py / chunk metadata tags
```

### Entity contract (summary)

Each entity has `id`, `name`, `class`, `aliases`, `tags`, `relations[]`, `evidence[]` (`doc_id`, `source_id`, `url`, `snippet`), plus `spot_checked` / `spot_check_notes`.

Extraction is **deterministic** (gazetteer regex over processed text). No invented places: gazetteer entries that never appear in the corpus are dropped.

Duplicate spellings (e.g. Kampong Glam / Gelam) are aliases on one `District` node.

## How to run

```bash
# Ensure processed docs exist
python scripts/crawl.py --force-manual
python scripts/normalize.py   # if needed

python scripts/build_ontology.py
python scripts/build_ontology.py --gate-only
pytest tests/test_phase3_ontology.py -q
```

## Exit criteria (gate → Phase 4)

- [x] `taxonomy.yaml` defines required classes, relations, tags
- [x] `schema.json` documents the entity shape
- [x] `entities.json` built from processed KB + gazetteer
- [x] ≥20 entities spot-checked with evidence snippets + source URLs
- [x] All five classes represented
- [x] Tests cover taxonomy, extract, gate, alias merge

### Decision table (Phase 3 → 4)

| Observation | Action in Phase 4 |
|-------------|-------------------|
| Dense typed entities + relations | Hybrid retrieval (Chroma + Neo4j GraphRAG) |
| Sparse graph / few relations | Chroma primary; graph optional |
| Poor extract / weak evidence | Seed hand list + vector-only until re-extract |

## Phase 3 status

**Complete** when `python scripts/build_ontology.py` exits 0 and `DECISIONS.md` records the gate. Phase 4 stores: see [`04-stores.md`](04-stores.md).
