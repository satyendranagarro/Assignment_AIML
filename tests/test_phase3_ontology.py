"""Phase 3 ontology tests (offline; uses processed docs or rebuilds from manual)."""

from __future__ import annotations

import json
from pathlib import Path

from src.crawl.runner import crawl_all
from src.data.normalize import normalize_all_raw
from src.data.sources import load_and_validate_sources
from src.ontology.extract import build_entities, load_gazetteer
from src.ontology.gate import evaluate_phase3_gate, write_entities_json
from src.ontology.taxonomy import load_taxonomy, validate_taxonomy
from src.ontology.validate import validate_entities

ROOT = Path(__file__).resolve().parents[1]


def _ensure_processed(tmp_path: Path) -> Path:
    sources, meta = load_and_validate_sources(ROOT / "data" / "sources.yaml")
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    crawl_all(
        sources,
        meta=meta,
        raw_dir=raw,
        manual_dir=ROOT / "data" / "manual",
        force_manual=True,
    )
    normalize_all_raw(sources, raw_dir=raw, processed_dir=processed)
    return processed


def test_taxonomy_has_required_classes_relations_tags():
    taxonomy = load_taxonomy(ROOT / "ontology" / "taxonomy.yaml")
    errors = validate_taxonomy(taxonomy)
    assert not errors, errors
    assert "Attraction" in taxonomy.classes
    assert "located_in" in taxonomy.relations
    assert "indoor" in taxonomy.tags


def test_gazetteer_has_at_least_twenty_seed_entities():
    gaz = load_gazetteer(ROOT / "ontology" / "gazetteer.yaml")
    assert len(gaz["entities"]) >= 20


def test_build_entities_spot_checks_at_least_twenty(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    entities = build_entities(
        gazetteer_path=ROOT / "ontology" / "gazetteer.yaml",
        processed_dir=processed,
        taxonomy=load_taxonomy(ROOT / "ontology" / "taxonomy.yaml"),
        min_spot_check=20,
    )
    assert len(entities) >= 20
    spot = [e for e in entities if e.spot_checked]
    assert len(spot) >= 20
    for e in spot:
        assert e.evidence, e.id
    errors = validate_entities(
        entities, taxonomy=load_taxonomy(ROOT / "ontology" / "taxonomy.yaml")
    )
    assert not errors, errors[:5]


def test_phase3_gate_passes_after_write(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    taxonomy = load_taxonomy(ROOT / "ontology" / "taxonomy.yaml")
    entities = build_entities(
        gazetteer_path=ROOT / "ontology" / "gazetteer.yaml",
        processed_dir=processed,
        taxonomy=taxonomy,
        min_spot_check=20,
    )
    out = tmp_path / "entities.json"
    write_entities_json(entities, out, taxonomy_path=ROOT / "ontology" / "taxonomy.yaml")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["spot_checked_count"] >= 20
    report = evaluate_phase3_gate(
        entities_path=out,
        taxonomy_path=ROOT / "ontology" / "taxonomy.yaml",
    )
    assert report.ok, report.messages


def test_kampong_glam_alias_merges_gelam_spelling(tmp_path: Path):
    processed = _ensure_processed(tmp_path)
    entities = build_entities(
        gazetteer_path=ROOT / "ontology" / "gazetteer.yaml",
        processed_dir=processed,
        min_spot_check=5,
    )
    by_id = {e.id: e for e in entities}
    assert "dist-kampong-glam" in by_id
    assert "Kampong Gelam" in by_id["dist-kampong-glam"].aliases
    assert by_id["dist-kampong-glam"].evidence


def test_build_ontology_script(tmp_path: Path):
    import importlib.util

    processed = _ensure_processed(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "build_ontology_script", ROOT / "scripts" / "build_ontology.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path / "entities.json"
    code = mod.main(
        [
            "--processed",
            str(processed),
            "--out",
            str(out),
            "--taxonomy",
            str(ROOT / "ontology" / "taxonomy.yaml"),
            "--gazetteer",
            str(ROOT / "ontology" / "gazetteer.yaml"),
        ]
    )
    assert code == 0
    assert out.is_file()
