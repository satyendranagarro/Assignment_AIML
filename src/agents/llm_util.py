"""Shared LLM invoke with observability + ConfigError surfacing."""

from __future__ import annotations

import time
from typing import Any

from src.llm.factory import ConfigError, get_chat_model, resolve_provider
from src.observability import log_event


def invoke_chat(
    messages: list[tuple[str, str]],
    *,
    provider: str | None = None,
    temperature: float = 0.2,
) -> tuple[str, str]:
    """Return (text, provider_name). Raises ConfigError if provider misconfigured."""
    name = resolve_provider(provider)
    t0 = time.perf_counter()
    log_event("llm.invoke", "Chat invoke", llm_provider=name, status="start")
    try:
        model = get_chat_model(name, temperature=temperature)
        # LangChain message tuples
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_msgs: list[Any] = []
        for role, content in messages:
            if role == "system":
                lc_msgs.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_msgs.append(AIMessage(content=content))
            else:
                lc_msgs.append(HumanMessage(content=content))
        result = model.invoke(lc_msgs)
        text = getattr(result, "content", None) or str(result)
        if isinstance(text, list):
            # Some providers return content blocks
            text = "".join(
                b.get("text", "") if isinstance(b, dict) else str(b) for b in text
            )
        log_event(
            "llm.invoke",
            "Chat invoke done",
            llm_provider=name,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            status="ok",
        )
        return str(text).strip(), name
    except ConfigError:
        log_event(
            "config_error",
            "LLM provider misconfigured",
            llm_provider=name,
            status="error",
        )
        raise
    except Exception as exc:  # noqa: BLE001
        log_event(
            "llm.error",
            "Chat invoke failed",
            llm_provider=name,
            status="error",
            error=str(exc)[:200],
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise


def session_notes(state: Any) -> str:
    parts = []
    if getattr(state, "traveler_type", None):
        parts.append(f"traveler={state.traveler_type}")
    if getattr(state, "prefer_indoor", None) is True:
        parts.append("prefer_indoor=true")
    if getattr(state, "prefer_indoor", None) is False:
        parts.append("prefer_indoor=false")
    if getattr(state, "budget_amount", None) is not None:
        parts.append(f"budget={state.budget_amount} {state.budget_currency or ''}".strip())
    if getattr(state, "interests", None):
        parts.append("interests=" + ",".join(state.interests))
    return "; ".join(parts)
