"""Phase 3 ontology package: taxonomy, gazetteer extract, validate, gate."""

from src.ontology.extract import build_entities, load_gazetteer
from src.ontology.gate import Phase3GateReport, evaluate_phase3_gate
from src.ontology.models import Entity, Evidence, Relation
from src.ontology.taxonomy import load_taxonomy, validate_taxonomy
from src.ontology.validate import validate_entities

__all__ = [
    "Entity",
    "Evidence",
    "Phase3GateReport",
    "Relation",
    "build_entities",
    "evaluate_phase3_gate",
    "load_gazetteer",
    "load_taxonomy",
    "validate_entities",
    "validate_taxonomy",
]
