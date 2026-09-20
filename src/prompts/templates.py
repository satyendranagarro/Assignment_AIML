"""Prompt helpers for grounded agent replies."""

from __future__ import annotations

from src.rag.models import RetrievalHit

SYSTEM_GROUNDING = """You are a helpful Singapore travel assistant (chat style).
Rules:
- Answer like ChatGPT: clear, conversational, well-structured. Lead with a direct answer.
- Use ONLY the knowledge-base excerpts for destination facts. Never invent attractions,
  prices, hours, or venues that are not in the excerpts.
- Do NOT paste raw excerpt text, markdown headers, or phrases like "based on the provided excerpts".
- If the excerpts are thin, say what is and is not covered in plain language.
- Prefer short sections or bullets when listing places; keep prose readable.
- Destination is Singapore unless the user asks about somewhere else (then refuse invention).
- Do not add a Sources section; citations are attached separately by the app.
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
        f"Knowledge-base excerpts (private context — do not dump verbatim):\n{context}\n\n"
        "Write a natural chat reply that answers the user using only those facts. "
        "Name places and tips that appear in the excerpts; skip inventing the rest."
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
        f"Knowledge-base excerpts (private context — do not dump verbatim):\n{context}\n"
        f"{wx}{fx}\n"
        "Write a natural day-wise Singapore plan in chat style. "
        "Prefer indoor options on rainy days. Do not invent places missing from excerpts."
    )
