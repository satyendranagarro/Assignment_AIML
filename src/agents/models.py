"""Shared agent models: intents, session state, labeled responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Intent = Literal[
    "rag_only",
    "weather_only",
    "currency_only",
    "combined_itinerary",
    "combined_budget",
    "clarify",
    "out_of_scope",
]

LabelKind = Literal["kb_fact", "mcp_data", "llm_suggestion", "error", "system"]

LABEL_PREFIX = {
    "kb_fact": "[KB fact]",
    "mcp_data": "[MCP data]",
    "llm_suggestion": "[LLM suggestion]",
    "error": "[Error]",
    "system": "[System]",
}


@dataclass
class SessionState:
    """Multi-turn conversation memory for A0."""

    session_id: str = ""
    traveler_type: str | None = None  # family | couple | solo | ...
    budget_amount: float | None = None
    budget_currency: str | None = None
    prefer_indoor: bool | None = None
    interests: list[str] = field(default_factory=list)
    destination: str = "Singapore"
    history: list[dict[str, str]] = field(default_factory=list)
    last_intent: Intent | None = None

    def update_from_utterance(self, text: str) -> None:
        lower = text.lower()
        if any(w in lower for w in ("family", "kids", "children", "child")):
            self.traveler_type = "family"
            if "family" not in self.interests:
                self.interests.append("family")
        if "couple" in lower:
            self.traveler_type = "couple"
        if "solo" in lower or "alone" in lower:
            self.traveler_type = "solo"
        if "indoor" in lower and ("prefer" in lower or "only" in lower or "rather" in lower):
            self.prefer_indoor = True
        if "outdoor" in lower and "prefer" in lower:
            self.prefer_indoor = False
        if "culture" in lower or "cultural" in lower:
            if "culture" not in self.interests:
                self.interests.append("culture")
        # Budget: "INR 60000" / "budget of 50000 USD"
        import re

        m = re.search(
            r"(?:budget(?:\s+of)?\s+)?(?P<cur>INR|USD|SGD|EUR|GBP)\s*(?P<amt>[\d,]+(?:\.\d+)?)",
            text,
            re.I,
        )
        if not m:
            m = re.search(
                r"(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<cur>INR|USD|SGD|EUR|GBP)",
                text,
                re.I,
            )
        if m:
            self.budget_currency = m.group("cur").upper()
            self.budget_amount = float(m.group("amt").replace(",", ""))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LabeledBlock:
    kind: LabelKind
    text: str
    citations: list[dict[str, str]] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        prefix = LABEL_PREFIX.get(self.kind, f"[{self.kind}]")
        body = self.text.strip()
        cite_lines = []
        for c in self.citations:
            title = c.get("title") or "source"
            url = c.get("url") or ""
            if url:
                cite_lines.append(f"- [{title}]({url})")
            else:
                cite_lines.append(f"- {title}")
        # Label on its own line so the body reads like a normal chat reply.
        if cite_lines:
            cites = "**Sources**\n" + "\n".join(cite_lines)
            return f"{prefix}\n\n{body}\n\n{cites}"
        return f"{prefix}\n\n{body}"


@dataclass
class AgentResponse:
    intent: Intent
    agent: str
    answer: str
    blocks: list[LabeledBlock] = field(default_factory=list)
    citations: list[dict[str, str]] = field(default_factory=list)
    used_mcp: bool = False
    used_rag: bool = False
    provider: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "agent": self.agent,
            "answer": self.answer,
            "blocks": [asdict(b) for b in self.blocks],
            "citations": self.citations,
            "used_mcp": self.used_mcp,
            "used_rag": self.used_rag,
            "provider": self.provider,
            "error": self.error,
            "meta": self.meta,
        }


def render_blocks(blocks: list[LabeledBlock]) -> str:
    return "\n\n".join(b.render() for b in blocks if b.text.strip())
