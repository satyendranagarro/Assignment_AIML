"""Deterministic intent router for A0 (no LLM required for routing tests)."""

from __future__ import annotations

import re

from src.agents.models import Intent

_OUT_OF_SCOPE = re.compile(
    r"\b(book|booking|reserve|reservation|hotel|flight|flights|airline|"
    r"payment|pay for|uber|grab ride|visa application)\b",
    re.I,
)
_WEATHER = re.compile(
    r"\b(weather|forecast|rain|raining|temperature|humid|umbrella|"
    r"indoor or outdoor|outdoor or indoor)\b",
    re.I,
)
_CURRENCY = re.compile(
    r"\b(convert|conversion|exchange rate|currency|fx|inr|usd|sgd|eur|gbp|"
    r"how much is|budget in)\b",
    re.I,
)
_ITINERARY = re.compile(
    r"\b(itinerary|day[- ]?wise|three[- ]day|3[- ]day|plan (a |my )?trip|"
    r"plan (a |my )?visit|suggest (a )?plan|sightseeing plan)\b",
    re.I,
)
_CLARIFY = re.compile(
    r"^(hi|hello|hey|help|what can you do)(\s*[!?.]*)?$",
    re.I,
)


def classify_intent(text: str) -> Intent:
    """Map user utterance → Intent. Prefer specific combined routes over single tools."""
    q = (text or "").strip()
    if not q:
        return "clarify"
    if _OUT_OF_SCOPE.search(q):
        return "out_of_scope"
    if _CLARIFY.match(q):
        return "clarify"

    wants_weather = bool(_WEATHER.search(q))
    wants_fx = bool(_CURRENCY.search(q))
    wants_plan = bool(_ITINERARY.search(q))
    # Outdoor attractions + rain/weather ⇒ combined
    outdoor_swap = bool(
        re.search(r"\boutdoor\b", q, re.I)
        and re.search(r"\b(indoor|rain|weather|forecast)\b", q, re.I)
    )
    family_weather = bool(
        re.search(r"\bfamily\b", q, re.I) and wants_weather
    )

    if (wants_plan or outdoor_swap or family_weather) and wants_weather:
        return "combined_itinerary"
    if wants_plan and wants_fx:
        return "combined_budget"
    if wants_fx and wants_plan:
        return "combined_budget"
    # Budget + itinerary phrasing without explicit "convert"
    if wants_plan and re.search(r"\bbudget\b", q, re.I):
        return "combined_budget"
    if wants_weather and not wants_plan and not outdoor_swap:
        return "weather_only"
    if wants_fx and not wants_plan:
        return "currency_only"
    return "rag_only"
