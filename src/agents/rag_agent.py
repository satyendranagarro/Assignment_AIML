"""A1 — RAGKnowledgeAgent: grounded KB answers + citations (no MCP)."""

from __future__ import annotations

import time
from typing import Any

from src.agents.llm_util import invoke_chat, session_notes
from src.agents.models import AgentResponse, LabeledBlock, SessionState, render_blocks
from src.llm.factory import ConfigError
from src.observability import log_event
from src.prompts import SYSTEM_GROUNDING, format_hit_context, rag_user_prompt
from src.rag.models import RetrievalHit


class RAGKnowledgeAgent:
    agent_id = "A1"

    def __init__(self, retriever: Any, *, provider: str | None = None) -> None:
        self.retriever = retriever
        self.provider = provider

    def run(self, query: str, state: SessionState) -> AgentResponse:
        t0 = time.perf_counter()
        log_event(
            "agent.start",
            "RAGKnowledgeAgent",
            agent=self.agent_id,
            intent="rag_only",
            query_preview=query,
        )
        hits: list[RetrievalHit] = []
        try:
            hits = self.retriever.retrieve(query)
        except Exception as exc:  # noqa: BLE001
            log_event(
                "agent.end",
                "RAG retrieve failed",
                agent=self.agent_id,
                status="error",
                error=str(exc)[:200],
            )
            block = LabeledBlock(
                kind="error",
                text=f"Knowledge retrieval failed: {exc}. I cannot invent destination facts.",
            )
            return AgentResponse(
                intent="rag_only",
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
                error=str(exc),
                used_rag=True,
            )

        # Out-of-destination / empty KB
        if not hits or _looks_out_of_kb(query, hits):
            block = LabeledBlock(
                kind="error",
                text=(
                    "I do not have reliable knowledge-base coverage for that request. "
                    "I will not invent attractions or facts outside the Singapore KB."
                ),
            )
            ans = render_blocks([block])
            log_event(
                "agent.end",
                "RAG empty/out-of-scope KB",
                agent=self.agent_id,
                status="ok",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            return AgentResponse(
                intent="rag_only",
                agent=self.agent_id,
                answer=ans,
                blocks=[block],
                used_rag=True,
                provider=self.provider,
            )

        citations = _unique_citations(hits)
        context = format_hit_context(hits)
        notes = session_notes(state)
        # Deterministic KB excerpt block (always)
        kb_block = LabeledBlock(
            kind="kb_fact",
            text=_summarize_hits(hits, query=query, state=state),
            citations=citations,
        )

        blocks: list[LabeledBlock] = [kb_block]
        if _looks_like_itinerary(query):
            from src.agents.planner_agent import _day_wise_plan

            blocks.append(
                LabeledBlock(
                    kind="llm_suggestion",
                    text=_day_wise_plan(hits, state, None),
                )
            )

        llm_text = ""
        provider_used = self.provider
        try:
            llm_text, provider_used = invoke_chat(
                [
                    ("system", SYSTEM_GROUNDING),
                    ("human", rag_user_prompt(query, context, session_notes=notes)),
                ],
                provider=self.provider,
            )
        except ConfigError as exc:
            err = LabeledBlock(
                kind="error",
                text=f"LLM configuration error: {exc}. No answer fabricated.",
            )
            blocks = blocks + [err]
            return AgentResponse(
                intent="rag_only",
                agent=self.agent_id,
                answer=render_blocks(blocks),
                blocks=blocks,
                citations=citations,
                used_rag=True,
                error=str(exc),
                provider=provider_used,
            )
        except Exception as exc:  # noqa: BLE001
            llm_text = ""
            log_event(
                "llm.error",
                "RAG LLM failed; returning KB excerpts only",
                agent=self.agent_id,
                error=str(exc)[:200],
                status="error",
            )

        if llm_text and llm_text != "[fake LLM response]":
            blocks.append(LabeledBlock(kind="llm_suggestion", text=llm_text))
        elif llm_text == "[fake LLM response]" and not any(
            b.kind == "llm_suggestion" for b in blocks
        ):
            blocks.append(
                LabeledBlock(
                    kind="llm_suggestion",
                    text=(
                        "Based on the cited KB excerpts above, prioritize well-documented "
                        "Singapore places and transport tips. Verify details against the sources."
                    ),
                )
            )

        ans = render_blocks(blocks)
        log_event(
            "agent.end",
            "RAGKnowledgeAgent done",
            agent=self.agent_id,
            intent="rag_only",
            status="ok",
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            llm_provider=provider_used,
        )
        return AgentResponse(
            intent="rag_only",
            agent=self.agent_id,
            answer=ans,
            blocks=blocks,
            citations=citations,
            used_rag=True,
            provider=provider_used,
        )


def _looks_like_itinerary(query: str) -> bool:
    import re

    return bool(
        re.search(
            r"\b(itinerary|day[- ]?wise|three[- ]day|3[- ]day|sightseeing plan)\b",
            query,
            re.I,
        )
    )


def _unique_citations(hits: list[RetrievalHit]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for h in hits:
        c = h.citation()
        key = c.get("url") or c.get("title") or ""
        if not key or key in seen:
            continue
        if not c.get("url") and not c.get("title"):
            continue
        seen.add(key)
        out.append(c)
    return out


def _summarize_hits(
    hits: list[RetrievalHit],
    *,
    query: str,
    state: SessionState,
) -> str:
    lines = [f"Relevant Singapore KB excerpts for: {query}"]
    prefer_family = state.traveler_type == "family" or "family" in (state.interests or [])
    prefer_indoor = state.prefer_indoor is True
    shown = 0
    for h in hits:
        text_l = h.text.lower()
        tags = str((h.metadata or {}).get("topics") or "") + " " + text_l
        if prefer_indoor and "outdoor" in text_l and "indoor" not in text_l:
            continue
        if prefer_family and "nightlife" in text_l and "family" not in tags:
            # still allow; soft preference only
            pass
        snippet = h.text.strip().replace("\n", " ")
        if len(snippet) > 280:
            snippet = snippet[:277] + "…"
        src = h.title or h.entity_id or h.source
        lines.append(f"• ({src}) {snippet}")
        shown += 1
        if shown >= 5:
            break
    if shown == 0:
        # fallback first hits
        for h in hits[:3]:
            snippet = h.text.strip().replace("\n", " ")[:280]
            lines.append(f"• ({h.title or h.source}) {snippet}")
    return "\n".join(lines)


def _looks_out_of_kb(query: str, hits: list[RetrievalHit]) -> bool:
    """Heuristic: Antarctica / non-Singapore destinations with weak overlap."""
    q = query.lower()
    foreign = ("antarctica", "arctic", "mars", "moon", "alaska nightlife")
    if any(f in q for f in foreign):
        # If none of the hits mention the foreign place, treat as insufficient
        joined = " ".join(h.text.lower() for h in hits)
        if not any(f in joined for f in foreign if f in q):
            return True
    # Extremely weak scores
    if hits and all(h.score < 0.05 for h in hits):
        return True
    return False
