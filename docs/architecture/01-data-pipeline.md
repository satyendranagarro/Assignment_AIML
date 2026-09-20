# Architecture — Phase 1: Data engineering

## Purpose

Register **≥3** public Singapore travel sources, map them to assignment topic coverage, and ship **ingest / normalize** tooling that preserves `title` + `url` citation metadata for later RAG answers.

Crawl/fetch is **Phase 2**. This phase only defines *what* to fetch and *how* raw dumps become citation-safe processed docs.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Source registry | `data/sources.yaml` | Canonical list of sources, seeds, hosts, license notes |
| Coverage matrix | `data/coverage_matrix.yaml` | Required topics ↔ covering `source_id`s + gate decision table |
| Ingest CLI | `scripts/ingest.py` | Validate registry + matrix; emit crawl plan |
| Normalize CLI | `scripts/normalize.py` | `data/raw/<source_id>/` → `data/processed/<source_id>/*.json` |
| Library | `src/data/` | Models, validation, HTML→text, gate report |

## Registered sources (≥3)

| ID | Title | Primary URL |
|----|-------|-------------|
| `wikivoyage-singapore` | Singapore – Travel guide at Wikivoyage | https://en.wikivoyage.org/wiki/Singapore |
| `visitsg-essentials` | Visit Singapore — Plan Your Trip / Travellers Essentials | https://www.visitsingapore.com/mice/en/tools-and-resources/plan-your-trip/ |
| `visitsg-itineraries` | Visit Singapore — Sample Itineraries | https://www.visitsingapore.com/travel-tips/travelling-to-singapore/itineraries/7-days-in-singapore/ |
| `visitsg-things-to-do` | Visit Singapore — Top Things to Do | https://www.visitsingapore.com/things-to-do/top-things-to-do/ |

Reuse: Wikivoyage is CC BY-SA 4.0 (attribute + share-alike). Visit Singapore pages are all-rights-reserved — Phase 2 must keep short educational excerpts or fall back to a **manual Markdown dump** with a `*.meta.json` sidecar (`title`, `url`, optional `topics`).

## Coverage matrix (required topics)

Assignment KB must cover attractions, neighbourhoods, transport, cultural/practical tips, food, sample itineraries, and indoor/outdoor suggestions. Each required topic in `coverage_matrix.yaml` lists ≥1 registered `covered_by` source. Topic `status` remains `planned` until Phase 2 content lands (`green` / `yellow` / `red`).

Optional topics: `climate` (static tips only — live weather is MCP), `family`.

## Pipeline shape

```text
data/sources.yaml
      │
      ▼
scripts/ingest.py  ──validate──► gate report + crawl_plan.json
      │
      │  (Phase 2) scripts/crawl.py → data/raw/<source_id>/*.{html,md}
      │                              + optional *.meta.json
      ▼
scripts/normalize.py → data/processed/<source_id>/<doc_id>.json
      │
      └─ fields: doc_id, source_id, title, url, text, topics
         (title/url = citation metadata for Phase 4–5 answers)
```

**Downstream (planned infra):** Phase **1.5** stands up `infra/neo4j/` + `infra/chroma/`. Phases 2–3 fill volumes; Phase 4 **loads** processed docs + ontology **into that infra**; Phase 5 agents **read the same stores**. Unit tests for Phase 1 stay file-only; live KB tests need 1.5 up.

### Normalized document contract

```json
{
  "doc_id": "wikivoyage-singapore__singapore__a1b2c3d4e5",
  "source_id": "wikivoyage-singapore",
  "title": "Singapore – Travel guide at Wikivoyage",
  "url": "https://en.wikivoyage.org/wiki/Singapore",
  "text": "...cleaned plain text...",
  "topics": ["districts", "attractions", "transport"],
  "extra": {}
}
```

## How to run (Phase 1)

```bash
pip install -r requirements.txt
python scripts/ingest.py
python scripts/ingest.py --write-plan data/processed/crawl_plan.json
python scripts/normalize.py   # no-op until raw dumps exist
pytest tests/test_phase1_data.py -q
```

## Exit criteria (gate → Phase 2)

- [x] ≥3 sources in `data/sources.yaml` with citation `title` + `url`
- [x] Coverage matrix maps every **required** assignment topic to ≥1 source
- [x] Ingest validates registry and prints a crawl plan (no network fetch)
- [x] Normalize preserves citations; works for HTML and manual Markdown dumps
- [x] Tests cover gate pass + citation preservation

### Decision table (Phase 1 → 2)

| Observation | Action in Phase 2 |
|-------------|-------------------|
| Topic gaps after first crawl | Targeted crawl of missing seed URLs |
| ToS / robots block | Manual dump under `data/raw/<source_id>/` + meta sidecar |
| Thin coverage | Add allowlisted seeds; re-run normalize |
| Full coverage | Light refresh crawl only |

**Next infra:** implement Phase **1.5** knowledge Compose ([`01b-knowledge-infra.md`](01b-knowledge-infra.md)) so Phase 4 can load into real Neo4j/Chroma and Phase 5 agents reuse them. File-based Phase 1–2 work does not require Docker.

## Phase 1 status

**Complete** for engineering gate (registry + matrix + tools). Content acquisition is Phase 2 (`02-crawl.md`). Knowledge store IaC is Phase 1.5 (`01b-knowledge-infra.md`).
