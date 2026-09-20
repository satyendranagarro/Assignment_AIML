"""Prompt helpers for grounded agent replies.

Structured with Google/Gemini-style XML tags for clear separation of
role, instructions, constraints, context, and task.
"""

from __future__ import annotations

from src.rag.models import RetrievalHit

SYSTEM_GROUNDING = """\
<role>
You are a helpful Singapore travel assistant. Reply in a clear, conversational chat style.
</role>

<instructions>
1. Lead with a direct answer, then add short sections or bullets when listing places.
2. Use ONLY the knowledge-base excerpts inside <context> for destination facts.
3. Prefer places and tips that appear in the excerpts; skip inventing the rest.
4. If excerpts are thin, say in plain language what is and is not covered.
5. Destination is Singapore unless the user asks about somewhere else.
</instructions>

<constraints>
- Never invent attractions, prices, hours, or venues that are not in the excerpts.
- Do not paste raw excerpt text, markdown headers, or phrases like "based on the provided excerpts".
- If the user asks about a destination other than Singapore, refuse invention; do not fabricate facts.
- Do not add a Sources section; citations are attached separately by the app.
</constraints>

<output_format>
Natural chat reply. Prefer short sections or bullets for lists; keep prose readable.
</output_format>
"""


def format_hit_context(hits: list[RetrievalHit], *, max_chars: int = 3500) -> str:
    parts: list[str] = []
    used = 0
    for i, h in enumerate(hits, 1):
        cite = f"{h.title} | {h.url}".strip(" |")
        block = (
            f'<excerpt id="{i}" source="{h.source}">\n'
            f"{cite}\n{h.text.strip()}\n"
            f"</excerpt>"
        )
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts) if parts else "(no excerpts)"


def rag_user_prompt(query: str, context: str, *, session_notes: str = "") -> str:
    notes = (
        f"<session_preferences>\n{session_notes}\n</session_preferences>\n\n"
        if session_notes
        else ""
    )
    return (
        f"<question>\n{query}\n</question>\n\n"
        f"{notes}"
        f"<context>\n"
        "Private knowledge-base excerpts — do not dump verbatim.\n"
        f"{context}\n"
        f"</context>\n\n"
        "<task>\n"
        "Write a natural chat reply that answers the user using only the facts in <context>. "
        "Name places and tips that appear in the excerpts; skip inventing the rest.\n"
        "</task>"
    )


def planner_user_prompt(
    query: str,
    context: str,
    *,
    weather_text: str = "",
    currency_text: str = "",
    session_notes: str = "",
) -> str:
    notes = (
        f"<session_preferences>\n{session_notes}\n</session_preferences>\n\n"
        if session_notes
        else ""
    )
    wx = f"<weather>\n{weather_text}\n</weather>\n\n" if weather_text else ""
    fx = f"<currency>\n{currency_text}\n</currency>\n\n" if currency_text else ""
    return (
        f"<question>\n{query}\n</question>\n\n"
        f"{notes}"
        f"<context>\n"
        "Private knowledge-base excerpts — do not dump verbatim.\n"
        f"{context}\n"
        f"</context>\n\n"
        f"{wx}{fx}"
        "<task>\n"
        "Write a natural day-wise Singapore plan in chat style using <context> "
        "and any <weather> / <currency> data. Prefer indoor options on rainy days. "
        "Do not invent places missing from the excerpts.\n"
        "</task>"
    )
