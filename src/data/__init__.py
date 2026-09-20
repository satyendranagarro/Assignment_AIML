"""Phase 1 data-engineering package: sources, coverage, normalize."""

from src.data.coverage import GateReport, evaluate_phase1_gate
from src.data.models import Citation, NormalizedDocument, Source
from src.data.normalize import normalize_all_raw, normalize_raw_payload
from src.data.sources import load_and_validate_sources

__all__ = [
    "Citation",
    "GateReport",
    "NormalizedDocument",
    "Source",
    "evaluate_phase1_gate",
    "load_and_validate_sources",
    "normalize_all_raw",
    "normalize_raw_payload",
]
