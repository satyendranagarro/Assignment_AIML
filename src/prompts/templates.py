"""Prompt helpers for grounded agent replies."""

from __future__ import annotations

from src.rag.models import RetrievalHit

SYSTEM_GROUNDING = """You are a Singapore travel assistant.
Rules:
- Use ONLY the provided knowledge-base excerpts for destination facts.
- Never invent attractions, prices, or opening hours not present in the excerpts.
- If excerpts are insufficient, say so clearly.
- Distinguish suggestions from facts.
- Destination is Singapore unless the user asks about somewhere else (then refuse invention).
"""


def format_hit_context(hits: list[RetrievalHit], *, max_chars: int = 3500) -> str:
    parts: list[str] = []
    used = 0
    for i, h in enumerate(hits, 1):
        cite = f"{h.title} | {h.url}".strip(" |")
        block = f"[{i}] ({h.source}) {cite}\n{h.text.strip()}"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts) if parts else "(no excerpts)"


def rag_user_prompt(query: str, context: str, *, session_notes: str = "") -> str:
    notes = f"\nSession preferences: {session_notes}\n" if session_notes else ""
    return (
        f"User question: {query}\n{notes}"
        f"Knowledge-base excerpts:\n{context}\n\n"
        "Answer using the excerpts. List citations by title/URL when stating facts."
    )


def planner_user_prompt(
    query: str,
    context: str,
    *,
    weather_text: str = "",
    currency_text: str = "",
    session_notes: str = "",
) -> str:
    wx = f"\nWeather (MCP):\n{weather_text}\n" if weather_text else ""
    fx = f"\nCurrency (MCP):\n{currency_text}\n" if currency_text else ""
    notes = f"\nSession preferences: {session_notes}\n" if session_notes else ""
    return (
        f"User request: {query}\n{notes}"
        f"Knowledge-base excerpts:\n{context}\n"
        f"{wx}{fx}\n"
        "Produce a day-wise plan. Prefer indoor options on rainy days. "
        "Do not invent places missing from excerpts."
    )
