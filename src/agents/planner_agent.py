"""A4 — CombinedPlannerAgent: RAG + weather and/or currency."""

from __future__ import annotations

import time
from typing import Any

from mcp_servers.currency.client import CurrencyClient
from mcp_servers.weather.client import WeatherClient, WeatherMCPError
from src.agents.currency_agent import CurrencyToolAgent
from src.agents.llm_util import invoke_chat, session_notes
from src.agents.models import AgentResponse, Intent, LabeledBlock, SessionState, render_blocks
from src.agents.rag_agent import RAGKnowledgeAgent, _summarize_hits, _unique_citations
from src.agents.weather_agent import WeatherToolAgent
from src.llm.factory import ConfigError
from src.observability import log_event
from src.prompts import SYSTEM_GROUNDING, format_hit_context, planner_user_prompt
from src.rag.models import RetrievalHit


class CombinedPlannerAgent:
    agent_id = "A4"

    def __init__(
        self,
        retriever: Any,
        *,
        weather: WeatherClient | None = None,
        currency: CurrencyClient | None = None,
        provider: str | None = None,
    ) -> None:
        self.retriever = retriever
        self.weather = weather or WeatherClient()
        self.currency = currency or CurrencyClient()
        self.provider = provider
        self._rag = RAGKnowledgeAgent(retriever, provider=provider)
        self._wx = WeatherToolAgent(self.weather)
        self._fx = CurrencyToolAgent(self.currency)

    def run(
        self,
        query: str,
        state: SessionState,
        *,
        intent: Intent = "combined_itinerary",
    ) -> AgentResponse:
        t0 = time.perf_counter()
        log_event(
            "agent.start",
            "CombinedPlannerAgent",
            agent=self.agent_id,
            intent=intent,
            query_preview=query,
        )
        blocks: list[LabeledBlock] = []
        citations: list[dict[str, str]] = []
        used_mcp = False
        used_rag = False
        meta: dict[str, Any] = {}
        weather_text = ""
        currency_text = ""
        error: str | None = None

        # --- RAG ---
        hits: list[RetrievalHit] = []
        try:
            rag_query = _planner_rag_query(query, state, intent)
            hits = self.retriever.retrieve(rag_query)
            used_rag = True
        except Exception as exc:  # noqa: BLE001
            blocks.append(
                LabeledBlock(
                    kind="error",
                    text=f"KB retrieval failed: {exc}. Cannot invent itinerary facts.",
                )
            )
            error = str(exc)

        if hits:
            citations = _unique_citations(hits)
            kb = LabeledBlock(
                kind="kb_fact",
                text=_summarize_hits(hits, query=query, state=state),
                citations=citations,
            )
            blocks.append(kb)

            # Indoor alternatives when rain / outdoor swap requested
            if any(d.get("rain_likely") for d in (meta.get("forecast", {}) or {}).get("days") or []) or (
                "indoor" in query.lower() and "outdoor" in query.lower()
            ):
                from src.agents.rag_agent import _clean_snippet

                indoor_hits = [
                    h
                    for h in hits
                    if "indoor" in h.text.lower()
                    or "museum" in h.text.lower()
                    or "mall" in h.text.lower()
                ]
                if indoor_hits:
                    blocks.append(
                        LabeledBlock(
                            kind="kb_fact",
                            text="Indoor-leaning options from the knowledge base:\n\n"
                            + "\n".join(
                                f"- **{h.title or h.source}** — {_clean_snippet(h.text, max_len=160)}"
                                for h in indoor_hits[:3]
                            ),
                            citations=_unique_citations(indoor_hits),
                        )
                    )
        elif used_rag and not error:
            blocks.append(
                LabeledBlock(
                    kind="error",
                    text="No KB excerpts found for planning. I will not invent places.",
                )
            )

        # --- Weather MCP (combined_itinerary) ---
        if intent == "combined_itinerary" or "weather" in query.lower() or "rain" in query.lower():
            try:
                log_event("mcp.call", "weather@A4", agent=self.agent_id, status="start")
                fc = self.weather.forecast(days=3, place=state.destination or "Singapore")
                weather_text = self.weather.format_forecast(fc)
                meta["forecast"] = fc
                used_mcp = True
                blocks.append(LabeledBlock(kind="mcp_data", text=weather_text))
                # Re-add indoor tips now that we know rain days
                rain_days = [d["date"] for d in fc.get("days") or [] if d.get("rain_likely")]
                if rain_days and hits:
                    blocks.append(
                        LabeledBlock(
                            kind="llm_suggestion",
                            text=(
                                f"On rainy day(s) {', '.join(rain_days)}, prefer indoor KB options "
                                "(museums, malls, indoor attractions) over exposed outdoor sites."
                            ),
                        )
                    )
            except WeatherMCPError as exc:
                log_event(
                    "mcp.error",
                    "weather@A4 failed",
                    agent=self.agent_id,
                    status="error",
                    error=str(exc)[:200],
                )
                blocks.append(
                    LabeledBlock(
                        kind="error",
                        text=f"Weather MCP unavailable: {exc}. No fabricated forecast.",
                    )
                )
                error = error or str(exc)

        # --- Currency MCP (combined_budget) ---
        if intent == "combined_budget" or "budget" in query.lower() or "convert" in query.lower():
            fx_resp = self._fx.run(query, state)
            used_mcp = used_mcp or fx_resp.used_mcp
            for b in fx_resp.blocks:
                blocks.append(b)
            if fx_resp.meta.get("conversion"):
                meta["conversion"] = fx_resp.meta["conversion"]
                currency_text = fx_resp.blocks[0].text if fx_resp.blocks else ""
            if fx_resp.error:
                error = error or fx_resp.error

        # --- Day-wise plan: prefer one chat-style LLM suggestion ---
        provider_used = self.provider
        plan = _day_wise_plan(hits, state, meta.get("forecast"))
        llm_plan = ""
        if hits:
            try:
                llm_plan, provider_used = invoke_chat(
                    [
                        ("system", SYSTEM_GROUNDING),
                        (
                            "human",
                            planner_user_prompt(
                                query,
                                format_hit_context(hits),
                                weather_text=weather_text,
                                currency_text=currency_text,
                                session_notes=session_notes(state),
                            ),
                        ),
                    ],
                    provider=self.provider,
                )
            except ConfigError as exc:
                blocks.append(
                    LabeledBlock(
                        kind="error",
                        text=f"LLM configuration error: {exc}. Plan below uses KB/MCP only.",
                    )
                )
                error = error or str(exc)
            except Exception as exc:  # noqa: BLE001
                log_event(
                    "llm.error",
                    "A4 LLM failed",
                    agent=self.agent_id,
                    error=str(exc)[:200],
                    status="error",
                )

        if llm_plan and llm_plan != "[fake LLM response]":
            blocks.append(LabeledBlock(kind="llm_suggestion", text=llm_plan.strip()))
        else:
            blocks.append(LabeledBlock(kind="llm_suggestion", text=plan))

        ans = render_blocks(blocks)
        log_event(
            "agent.end",
            "CombinedPlannerAgent done",
            agent=self.agent_id,
            intent=intent,
            status="ok" if not error else "error",
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            llm_provider=provider_used,
        )
        return AgentResponse(
            intent=intent,
            agent=self.agent_id,
            answer=ans,
            blocks=blocks,
            citations=citations,
            used_mcp=used_mcp,
            used_rag=used_rag,
            provider=provider_used,
            error=error,
            meta=meta,
        )


def _planner_rag_query(query: str, state: SessionState, intent: Intent) -> str:
    parts = [query, "Singapore itinerary attractions districts transport"]
    if state.traveler_type == "family" or "family" in query.lower():
        parts.append("family children")
    if state.prefer_indoor or "indoor" in query.lower():
        parts.append("indoor attractions")
    if "culture" in query.lower() or "culture" in (state.interests or []):
        parts.append("cultural neighbourhoods heritage")
    if intent == "combined_budget":
        parts.append("budget sightseeing")
    return " ".join(parts)


def _day_wise_plan(
    hits: list[RetrievalHit],
    state: SessionState,
    forecast: dict[str, Any] | None,
) -> str:
    """Deterministic 3-day skeleton from KB hits + optional rain flags."""
    titles: list[str] = []
    for h in hits:
        name = h.title or h.entity_id
        if name and name not in titles:
            titles.append(name)
        if len(titles) >= 9:
            break
    while len(titles) < 3:
        titles.append("Singapore city highlights (see KB citations)")

    days_meta = (forecast or {}).get("days") or []
    lines = ["Day-wise Singapore plan (grounded in KB; weather-aware when MCP available):"]
    for i in range(3):
        day_label = days_meta[i]["date"] if i < len(days_meta) else f"Day {i + 1}"
        rain = bool(i < len(days_meta) and days_meta[i].get("rain_likely"))
        picks = titles[i * 3 : (i + 1) * 3] or titles[:3]
        focus = "indoor-leaning" if rain or state.prefer_indoor else "mixed indoor/outdoor"
        fam = " (family-friendly bias)" if state.traveler_type == "family" else ""
        rain_note = " — rain likely: prefer indoor alternatives" if rain else ""
        lines.append(
            f"Day {i + 1} ({day_label}) [{focus}]{fam}{rain_note}: " + "; ".join(picks)
        )
    if state.budget_amount is not None and state.budget_currency:
        lines.append(
            f"Budget context: {state.budget_amount} {state.budget_currency} "
            "(from session / MCP conversion)."
        )
    return "\n".join(lines)
