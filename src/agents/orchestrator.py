"""A0 — OrchestratorAgent: intent route, session state, dispatch A1–A4."""

from __future__ import annotations

import time
import uuid
from typing import Any

from mcp_servers.currency.client import CurrencyClient
from mcp_servers.weather.client import WeatherClient
from src.agents.currency_agent import CurrencyToolAgent
from src.agents.models import AgentResponse, Intent, LabeledBlock, SessionState, render_blocks
from src.agents.planner_agent import CombinedPlannerAgent
from src.agents.rag_agent import RAGKnowledgeAgent
from src.agents.router import classify_intent
from src.agents.weather_agent import WeatherToolAgent
from src.llm.factory import ConfigError, resolve_provider
from src.observability import bind_context, log_event, new_correlation_id


class OrchestratorAgent:
    agent_id = "A0"

    def __init__(
        self,
        retriever: Any,
        *,
        weather: WeatherClient | None = None,
        currency: CurrencyClient | None = None,
        provider: str | None = None,
        session: SessionState | None = None,
    ) -> None:
        self.retriever = retriever
        self.weather = weather or WeatherClient()
        self.currency = currency or CurrencyClient()
        self.provider = provider
        self.session = session or SessionState(session_id=uuid.uuid4().hex[:10])
        self.rag = RAGKnowledgeAgent(retriever, provider=provider)
        self.wx = WeatherToolAgent(self.weather)
        self.fx = CurrencyToolAgent(self.currency)
        self.planner = CombinedPlannerAgent(
            retriever,
            weather=self.weather,
            currency=self.currency,
            provider=provider,
        )

    def set_provider(self, provider: str) -> None:
        prev = self.provider
        self.provider = provider
        self.rag.provider = provider
        self.planner.provider = provider
        if prev and prev != provider:
            log_event(
                "llm.provider_changed",
                f"{prev} → {provider}",
                llm_provider=provider,
                status="ok",
            )
        bind_context(llm_provider=provider)

    def handle(self, user_text: str, *, correlation_id: str | None = None) -> AgentResponse:
        cid = correlation_id or new_correlation_id()
        try:
            provider = resolve_provider(self.provider)
        except ConfigError as exc:
            bind_context(
                correlation_id=cid,
                session_id=self.session.session_id,
                llm_provider=self.provider,
            )
            block = LabeledBlock(
                kind="error",
                text=f"LLM configuration error: {exc}. No silent fallback; no fabricated answer.",
            )
            log_event("config_error", str(exc), status="error")
            return AgentResponse(
                intent="clarify",
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
                error=str(exc),
                provider=self.provider,
            )

        bind_context(
            correlation_id=cid,
            session_id=self.session.session_id,
            llm_provider=provider,
        )
        t0 = time.perf_counter()
        log_event(
            "request.start",
            "User turn",
            query_preview=user_text,
            llm_provider=provider,
        )

        self.session.update_from_utterance(user_text)
        intent = classify_intent(user_text)
        self.session.last_intent = intent
        log_event(
            "agent.start",
            "Orchestrator route",
            agent=self.agent_id,
            intent=intent,
            query_preview=user_text,
        )

        try:
            response = self._dispatch(intent, user_text)
        except ConfigError as exc:
            block = LabeledBlock(
                kind="error",
                text=f"LLM configuration error: {exc}. No silent fallback; no fabricated answer.",
            )
            response = AgentResponse(
                intent=intent,
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
                error=str(exc),
                provider=provider,
            )
        except Exception as exc:  # noqa: BLE001
            log_event(
                "agent.end",
                "Orchestrator failure",
                agent=self.agent_id,
                status="error",
                error=str(exc)[:200],
            )
            block = LabeledBlock(
                kind="error",
                text=f"Something went wrong handling your request: {exc}",
            )
            response = AgentResponse(
                intent=intent,
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
                error=str(exc),
                provider=provider,
            )

        response.provider = response.provider or provider
        response.intent = intent
        self.session.history.append({"role": "user", "content": user_text})
        self.session.history.append({"role": "assistant", "content": response.answer[:2000]})

        log_event(
            "request.end",
            "User turn done",
            intent=intent,
            agent=response.agent,
            status="ok" if not response.error else "error",
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            llm_provider=response.provider,
        )
        log_event(
            "agent.end",
            "Orchestrator done",
            agent=self.agent_id,
            intent=intent,
            status="ok" if not response.error else "error",
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return response

    def _dispatch(self, intent: Intent, user_text: str) -> AgentResponse:
        if intent == "out_of_scope":
            block = LabeledBlock(
                kind="system",
                text=(
                    "That request is out of scope for this assistant. "
                    "I can help with Singapore destination knowledge, weather, "
                    "currency conversion, and weather/budget-aware itineraries — "
                    "not hotel/flight booking or payments."
                ),
            )
            return AgentResponse(
                intent=intent,
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
            )
        if intent == "clarify":
            block = LabeledBlock(
                kind="system",
                text=(
                    "I can answer Singapore travel questions from the knowledge base, "
                    "fetch weather via MCP, convert currency via MCP, or build a "
                    "combined itinerary. What would you like to do?"
                ),
            )
            return AgentResponse(
                intent=intent,
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
            )
        if intent == "rag_only":
            return self.rag.run(user_text, self.session)
        if intent == "weather_only":
            return self.wx.run(user_text, self.session)
        if intent == "currency_only":
            return self.fx.run(user_text, self.session)
        if intent in ("combined_itinerary", "combined_budget"):
            return self.planner.run(user_text, self.session, intent=intent)
        return self.rag.run(user_text, self.session)
