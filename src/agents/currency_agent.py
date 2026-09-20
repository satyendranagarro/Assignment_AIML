"""A3 — CurrencyToolAgent via MCP currency client."""

from __future__ import annotations

import re
import time
from typing import Any

from mcp_servers.currency.client import CurrencyClient, CurrencyMCPError
from src.agents.models import AgentResponse, LabeledBlock, SessionState, render_blocks
from src.observability import log_event

_CUR = r"INR|USD|SGD|EUR|GBP"


class CurrencyToolAgent:
    agent_id = "A3"

    def __init__(self, client: CurrencyClient | None = None) -> None:
        self.client = client or CurrencyClient()

    def run(self, query: str, state: SessionState) -> AgentResponse:
        t0 = time.perf_counter()
        log_event(
            "agent.start",
            "CurrencyToolAgent",
            agent=self.agent_id,
            intent="currency_only",
            query_preview=query,
        )
        parsed = _parse_conversion(query, state)
        if parsed is None:
            block = LabeledBlock(
                kind="system",
                text=(
                    "Please provide an amount and currencies to convert "
                    "(e.g. 'Convert INR 50000 to SGD'). "
                    "I can also use a budget stored earlier in this session."
                ),
            )
            return AgentResponse(
                intent="currency_only",
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
            )

        amount, src, dst = parsed
        try:
            log_event("mcp.call", "currency", agent=self.agent_id, status="start")
            payload = self.client.convert(amount, src, dst)
            text = self.client.format(payload)
            log_event(
                "mcp.call",
                "currency ok",
                agent=self.agent_id,
                status="ok",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
            # Persist budget in destination currency when converting travel budget
            state.budget_amount = float(payload.get("converted") or amount)
            state.budget_currency = dst
            block = LabeledBlock(kind="mcp_data", text=text, meta=payload)
            ans = render_blocks([block])
            log_event(
                "agent.end",
                "CurrencyToolAgent done",
                agent=self.agent_id,
                status="ok",
            )
            return AgentResponse(
                intent="currency_only",
                agent=self.agent_id,
                answer=ans,
                blocks=[block],
                used_mcp=True,
                meta={"conversion": payload},
            )
        except CurrencyMCPError as exc:
            log_event(
                "mcp.error",
                "currency failed",
                agent=self.agent_id,
                status="error",
                error=str(exc)[:200],
            )
            block = LabeledBlock(
                kind="error",
                text=(
                    f"Currency MCP unavailable: {exc}. "
                    "I will not fabricate exchange rates."
                ),
            )
            return AgentResponse(
                intent="currency_only",
                agent=self.agent_id,
                answer=block.render(),
                blocks=[block],
                used_mcp=True,
                error=str(exc),
            )


def _parse_conversion(
    query: str, state: SessionState
) -> tuple[float, str, str] | None:
    # "Convert INR 50000 to SGD" / "How much is 200 SGD in INR"
    m = re.search(
        rf"convert\s+(?P<cur>{_CUR})\s*(?P<amt>[\d,]+(?:\.\d+)?)\s+to\s+(?P<dst>{_CUR})",
        query,
        re.I,
    )
    if m:
        return float(m.group("amt").replace(",", "")), m.group("cur").upper(), m.group("dst").upper()

    m = re.search(
        rf"(?:how much is|convert)\s+(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<cur>{_CUR})\s+(?:in|to)\s+(?P<dst>{_CUR})",
        query,
        re.I,
    )
    if m:
        return float(m.group("amt").replace(",", "")), m.group("cur").upper(), m.group("dst").upper()

    m = re.search(
        rf"(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<cur>{_CUR})\s+(?:in|to)\s+(?P<dst>{_CUR})",
        query,
        re.I,
    )
    if m:
        return float(m.group("amt").replace(",", "")), m.group("cur").upper(), m.group("dst").upper()

    # "Convert my travel budget from USD to Singapore dollars"
    m = re.search(
        rf"(?:from\s+)?(?P<cur>{_CUR})\s+to\s+(?P<dst>{_CUR}|singapore dollars?)",
        query,
        re.I,
    )
    if m:
        dst = m.group("dst").upper()
        if "SINGAPORE" in dst:
            dst = "SGD"
        src = m.group("cur").upper()
        if state.budget_amount is not None and (
            not state.budget_currency or state.budget_currency.upper() == src
        ):
            return float(state.budget_amount), src, dst
        # amount missing
        return None

    # "Show my budget in SGD"
    m = re.search(rf"(?:budget|show).*\b(?:in|to)\s+(?P<dst>{_CUR})\b", query, re.I)
    if m and state.budget_amount is not None and state.budget_currency:
        return float(state.budget_amount), state.budget_currency.upper(), m.group("dst").upper()

    # Stored budget + implicit SGD destination
    if state.budget_amount is not None and state.budget_currency and re.search(
        r"singapore dollars?|sgd|destination currency", query, re.I
    ):
        return float(state.budget_amount), state.budget_currency.upper(), "SGD"

    return None
