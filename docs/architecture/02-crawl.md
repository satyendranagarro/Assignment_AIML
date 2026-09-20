# Architecture — Phase 2: Allowlisted crawl

## Purpose

Fetch registered seed URLs into `data/raw/<source_id>/` with citation sidecars, fall back to committed manual dumps when robots/ToS block automation, normalize into `data/processed/`, and mark every **required** coverage-matrix topic **green**.

## Inputs / outputs

| Artifact | Path | Role |
|----------|------|------|
| Source registry | `data/sources.yaml` | Seeds, allowlist hosts, UA / delay / robots defaults |
| Manual fallbacks | `data/manual/<source_id>/` | Committed educational excerpts (+ `*.meta.json`) |
| Raw dumps | `data/raw/<source_id>/` | Crawl or copied manual bodies (gitignored) |
| Processed docs | `data/processed/<source_id>/` | Normalized JSON for Phase 3+ (gitignored) |
| Coverage matrix | `data/coverage_matrix.yaml` | Topic statuses updated by crawl gate |
| Crawl CLI | `scripts/crawl.py` | Fetch → normalize → buckets → gate |
| Library | `src/crawl/` | Fetch, robots, store, runner, buckets, gate |

## Crawl policy

1. **Allowlisted BFS** — start from each `seed_urls` entry; follow same-host links.
   - `defaults.max_depth: null` (or CLI `--max-depth none`) = unbounded depth (“whole site”).
   - `defaults.max_pages: 100` (or CLI `--max-pages`) = hard cap of attempts per source.
   - `--max-depth 0` = seeds only (no link follow).
2. **Allowlist** — host must match `allowlist_hosts` (www / bare variants accepted). Off-host links are ignored.
3. **Singapore path scope** — optional `url_path_prefixes` / `url_path_contains` keep BFS on destination pages (e.g. Wikivoyage `/wiki/Singapore…` or path containing `Singapore`). Empty = host-only filter (Visit Singapore site is already destination-bound).
4. **robots.txt** — respected when `defaults.respect_robots_txt: true`. If `robots.txt` is missing or returns 403/404, fetches are allowed (same as urllib when no robots file exists).
5. **Throttle** — `defaults.request_delay_seconds` between requests.
6. **ARR sources** (Visit Singapore) — store educational **Markdown excerpts**, not full HTML mirrors. Link discovery still uses the original HTML.
7. **Fallback** — if fetch fails or robots block, copy `data/manual/<source_id>/` into raw.

### Sidecar contract

Each raw file `page.html` (or `.md`) has sibling `page.html.meta.json`:

```json
{
  "title": "…",
  "url": "https://…",
  "topics": ["attractions"],
  "fetched_at": "2026-09-20T…",
  "fetch_mode": "crawl|excerpt|manual",
  "status_code": 200,
  "chars": 1234
}
```

## Topic buckets

After normalize, each matrix topic is scored from processed docs whose `source_id` is in that topic’s `covered_by` list:

| Status | Rule (defaults) |
|--------|-----------------|
| green | ≥1 doc and ≥800 chars |
| yellow | ≥1 doc and ≥200 chars |
| red | missing / thinner than yellow |

**Phase 2 exit:** every **required** topic is green, and every registered source has ≥1 raw file.

## How to run

```bash
pip install -r requirements.txt

# Reproducible offline path (manual packs only)
python scripts/crawl.py --force-manual --update-matrix

# Live allowlisted BFS crawl (unbounded depth, max_pages from yaml; manual fallback)
python scripts/crawl.py --update-matrix

# Seeds only
python scripts/crawl.py --max-depth 0 --update-matrix

# Re-score existing raw/processed
python scripts/crawl.py --gate-only

pytest tests/test_phase1_data.py tests/test_phase2_crawl.py -q
```

Useful flags: `--source-id <id>`, `--max-depth`, `--max-pages`, `--no-manual-fallback`, `--skip-normalize`, `--json`.

## Exit criteria (gate → Phase 3)

- [x] Allowlisted BFS crawl CLI with robots + delay + max_depth/max_pages
- [x] Raw dumps retain title + URL sidecars
- [x] Manual dumps for Visit Singapore (and Wikivoyage offline fallback)
- [x] Thin/SPA or HTTP-blocked fetches fall back to manual packs
- [x] Topic buckets evaluated; required topics green after crawl/normalize
- [x] Crawl reproducible via `--force-manual` or live seeds + fallback
- [x] Tests cover allowlist, excerpt mode, robots→manual fallback, BFS depth/page caps, matrix update

### Decision table (Phase 2 → 3)

| Observation | Action in Phase 3 |
|-------------|-------------------|
| Clear named entities (places, districts, modes) | Full ontology + relations |
| Mostly unstructured prose | Light taxonomy tags only |
| Duplicate near-identical dumps | Merge / dedupe before ontology |

## Phase 2 status

**Complete** when `python scripts/crawl.py --update-matrix` exits 0 and `DECISIONS.md` records the gate. Next: Phase 3 ontology (`03-ontology.md`).
