"""A1 — RAGKnowledgeAgent: grounded KB answers + citations (no MCP)."""

from __future__ import annotations

import re
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
        blocks: list[LabeledBlock] = []
        llm_text = ""
        provider_used = self.provider
        llm_error: str | None = None

        try:
            llm_text, provider_used = invoke_chat(
                [
                    ("system", SYSTEM_GROUNDING),
                    ("human", rag_user_prompt(query, context, session_notes=notes)),
                ],
                provider=self.provider,
            )
        except ConfigError as exc:
            llm_error = str(exc)
            err = LabeledBlock(
                kind="error",
                text=f"LLM configuration error: {exc}. No answer fabricated.",
            )
            # Still return grounded fallback from KB so the user sees facts.
            blocks = [
                LabeledBlock(
                    kind="kb_fact",
                    text=_summarize_hits(hits, query=query, state=state),
                    citations=citations,
                ),
                err,
            ]
            return AgentResponse(
                intent="rag_only",
                agent=self.agent_id,
                answer=render_blocks(blocks),
                blocks=blocks,
                citations=citations,
                used_rag=True,
                error=llm_error,
                provider=provider_used,
            )
        except Exception as exc:  # noqa: BLE001
            llm_text = ""
            log_event(
                "llm.error",
                "RAG LLM failed; returning KB summary only",
                agent=self.agent_id,
                error=str(exc)[:200],
                status="error",
            )

        # Grounded chat answer lives in [KB fact] (assignment label + natural prose).
        if llm_text and llm_text != "[fake LLM response]":
            kb_text = llm_text.strip()
        else:
            kb_text = _summarize_hits(hits, query=query, state=state)

        blocks.append(
            LabeledBlock(kind="kb_fact", text=kb_text, citations=citations)
        )

        if _looks_like_itinerary(query):
            from src.agents.planner_agent import _day_wise_plan

            blocks.append(
                LabeledBlock(
                    kind="llm_suggestion",
                    text=_day_wise_plan(hits, state, None),
                )
            )
        elif llm_text == "[fake LLM response]":
            # Offline / fake provider: short planning nudge without dumping excerpts again.
            blocks.append(
                LabeledBlock(
                    kind="llm_suggestion",
                    text=(
                        "Use the places above as a starting list, then group nearby "
                        "sights into half-day walks and verify details on the cited pages."
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


def _clean_snippet(text: str, *, max_len: int = 220) -> str:
    """Drop markdown chrome so offline fallback reads like a short note."""
    keep: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            s = s.lstrip("#").strip()
            if s.lower().startswith("visit singapore") or "educational excerpt" in s.lower():
                continue
        if s.lower().startswith("source:"):
            continue
        if s.lower().startswith("curated ") and "rag" in s.lower():
            continue
        keep.append(s)
    joined = " ".join(keep) if keep else text.strip().replace("\n", " ")
    joined = re.sub(r"\s+", " ", joined).strip()
    if len(joined) > max_len:
        return joined[: max_len - 1] + "…"
    return joined


def _summarize_hits(
    hits: list[RetrievalHit],
    *,
    query: str,
    state: SessionState,
) -> str:
    """Readable offline/fallback KB answer (not a raw chunk dump)."""
    prefer_indoor = state.prefer_indoor is True
    bullets: list[str] = []
    for h in hits:
        text_l = h.text.lower()
        if prefer_indoor and "outdoor" in text_l and "indoor" not in text_l:
            continue
        snippet = _clean_snippet(h.text)
        if not snippet:
            continue
        src = h.title or h.entity_id or h.source
        bullets.append(f"- **{src}** — {snippet}")
        if len(bullets) >= 5:
            break
    if not bullets:
        for h in hits[:3]:
            snippet = _clean_snippet(h.text)
            bullets.append(f"- **{h.title or h.source}** — {snippet}")

    intro = (
        f"Here is what the Singapore knowledge base covers for “{query.strip()}”:"
    )
    return intro + "\n\n" + "\n".join(bullets)


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
