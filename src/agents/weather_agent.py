"""A2 — WeatherToolAgent via MCP weather client."""

from __future__ import annotations

import re
import time
from typing import Any

from mcp_servers.weather.client import WeatherClient, WeatherMCPError
from src.agents.models import AgentResponse, LabeledBlock, SessionState, render_blocks
from src.observability import log_event


class WeatherToolAgent:
    agent_id = "A2"

    def __init__(self, client: WeatherClient | None = None) -> None:
        self.client = client or WeatherClient()

    def run(self, query: str, state: SessionState) -> AgentResponse:
        t0 = time.perf_counter()
        log_event(
            "agent.start",
            "WeatherToolAgent",
            agent=self.agent_id,
            intent="weather_only",
            query_preview=query,
        )
        place = state.destination or "Singapore"
        want_forecast = bool(
            re.search(r"forecast|next|days|tomorrow|rain|trip|indoor|outdoor", query, re.I)
        )
        blocks: list[LabeledBlock] = []
        meta: dict[str, Any] = {}
        try:
            log_event("mcp.call", "weather", agent=self.agent_id, status="start")
            if want_forecast or "current" not in query.lower():
                days = 3
                m = re.search(r"(\d+)\s*day", query, re.I)
                if m:
                    days = int(m.group(1))
                payload = self.client.forecast(days=days, place=place)
                text = self.client.format_forecast(payload)
                meta["forecast"] = payload
                blocks.append(LabeledBlock(kind="mcp_data", text=text, meta={"tool": "forecast"}))
                # Also include current for "what is the weather"
                if re.search(r"\b(current|now|today|what is the weather)\b", query, re.I):
                    cur = self.client.current(place=place)
                    blocks.insert(
                        0,
                        LabeledBlock(
                            kind="mcp_data",
                            text=self.client.format_current(cur),
                            meta={"tool": "current"},
                        ),
                    )
                    meta["current"] = cur
            else:
                cur = self.client.current(place=place)
                meta["current"] = cur
                blocks.append(
                    LabeledBlock(
                        kind="mcp_data",
                        text=self.client.format_current(cur),
                        meta={"tool": "current"},
                    )
                )

            if re.search(r"indoor|outdoor", query, re.I):
                rain = False
                fc = meta.get("forecast") or {}
                for d in (fc.get("days") or [])[:2]:
                    if d.get("rain_likely"):
                        rain = True
                        break
                suggestion = (
                    "Rain is likely soon — prefer indoor attractions tomorrow."
                    if rain
                    else "Rain looks unlikely — outdoor activities are reasonable, with a backup indoor option."
                )
                blocks.append(LabeledBlock(kind="llm_suggestion", text=suggestion))

            log_event(
                "mcp.call",
                "weather ok",
                agent=self.agent_id,
                status="ok",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
        except WeatherMCPError as exc:
            log_event(
                "mcp.error",
                "weather failed",
                agent=self.agent_id,
                status="error",
                error=str(exc)[:200],
            )
            blocks = [
                LabeledBlock(
                    kind="error",
                    text=(
                        f"Weather MCP unavailable: {exc}. "
                        "I will not fabricate temperatures or forecasts."
                    ),
                )
            ]
            ans = render_blocks(blocks)
            log_event(
                "agent.end",
                "WeatherToolAgent error",
                agent=self.agent_id,
                status="error",
            )
            return AgentResponse(
                intent="weather_only",
                agent=self.agent_id,
                answer=ans,
                blocks=blocks,
                used_mcp=True,
                error=str(exc),
            )

        ans = render_blocks(blocks)
        log_event(
            "agent.end",
            "WeatherToolAgent done",
            agent=self.agent_id,
            status="ok",
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        return AgentResponse(
            intent="weather_only",
            agent=self.agent_id,
            answer=ans,
            blocks=blocks,
            used_mcp=True,
            meta=meta,
        )
