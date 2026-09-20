"""Streamlit UI — Singapore AI Travel Planning Assistant (Phase 5)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Repo root on path for `src.*` / `mcp_servers.*`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

# Project .env is source of truth for the UI (overrides sticky shell exports).
load_dotenv(ROOT / ".env", override=True)

from src.agents import OrchestratorAgent, SessionState, build_retriever  # noqa: E402
from src.agents.models import LABEL_PREFIX, LabeledBlock  # noqa: E402
from src.llm.factory import (  # noqa: E402
    ConfigError,
    list_providers,
    resolve_embedding_provider,
    resolve_provider,
)
from src.observability import bind_context, log_event  # noqa: E402
from mcp_servers.currency.client import CurrencyClient  # noqa: E402
from mcp_servers.weather.client import WeatherClient  # noqa: E402


st.set_page_config(page_title="Singapore Travel Assistant", page_icon="🇸🇬", layout="wide")

_CHAT_KINDS = frozenset({"llm_suggestion", "error", "system"})
_DETAIL_KINDS = frozenset({"kb_fact", "mcp_data"})
_EXPANDER_TITLE = {
    "kb_fact": "KB fact — sources & excerpts",
    "mcp_data": "MCP data — live / tool result",
}


def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_session" not in st.session_state:
        st.session_state.agent_session = SessionState(session_id="ui")
    if "llm_provider" not in st.session_state:
        try:
            st.session_state.llm_provider = resolve_provider(None)
        except ConfigError:
            st.session_state.llm_provider = os.getenv("LLM_PROVIDER") or "openai"
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "retriever_error" not in st.session_state:
        st.session_state.retriever_error = None


@st.cache_resource(show_spinner="Loading knowledge stores…")
def _cached_retriever(embedding_provider: str, mock_mcp: bool):
    _ = mock_mcp  # cache key only
    return build_retriever(embedding_provider=embedding_provider)


def _embedding_provider_for(chat_provider: str) -> str:
    """Resolve embeddings after .env load; keep fake chat → fake emb when unset."""
    if chat_provider == "fake" and not (os.getenv("EMBEDDING_PROVIDER") or "").strip():
        return "fake"
    return resolve_embedding_provider(None)


def _get_orchestrator(provider: str) -> OrchestratorAgent:
    mock = (os.getenv("MCP_MOCK_MODE") or "").strip().lower() in {"1", "true", "yes"}
    emb = _embedding_provider_for(provider)
    try:
        retriever = _cached_retriever(emb, mock)
        st.session_state.retriever_error = None
    except Exception as exc:  # noqa: BLE001
        st.session_state.retriever_error = str(exc)
        raise

    orch = st.session_state.orchestrator
    if orch is None:
        orch = OrchestratorAgent(
            retriever,
            weather=WeatherClient(mock=mock),
            currency=CurrencyClient(mock=mock),
            provider=provider,
            session=st.session_state.agent_session,
        )
        st.session_state.orchestrator = orch
    else:
        orch.set_provider(provider)
        orch.session = st.session_state.agent_session
    return orch


def _blocks_from_payload(raw: list[dict[str, Any]] | None) -> list[LabeledBlock]:
    if not raw:
        return []
    out: list[LabeledBlock] = []
    for item in raw:
        kind = item.get("kind")
        text = (item.get("text") or "").strip()
        if not kind or not text:
            continue
        out.append(
            LabeledBlock(
                kind=kind,  # type: ignore[arg-type]
                text=text,
                citations=list(item.get("citations") or []),
                meta=dict(item.get("meta") or {}),
            )
        )
    return out


def _render_block_body(block: LabeledBlock) -> None:
    """Chat-style body: prose + optional sources (no assignment label prefix)."""
    st.markdown(block.text.strip())
    if block.citations:
        cite_lines = []
        for c in block.citations:
            title = c.get("title") or "source"
            url = c.get("url") or ""
            if url:
                cite_lines.append(f"- [{title}]({url})")
            else:
                cite_lines.append(f"- {title}")
        st.markdown("**Sources**\n" + "\n".join(cite_lines))


def _render_assistant_message(
    *,
    content: str,
    blocks: list[LabeledBlock] | None = None,
    meta_caption: str | None = None,
) -> None:
    """
    Chat-first layout:
    - LLM / error / system → main bubble text
    - KB fact / MCP data → collapsed expanders (closed by default)
    When there is no chat-layer block, KB/MCP are shown as the chat reply
    so weather/currency/RAG-only answers stay visible.
    """
    blocks = blocks or []
    chat_blocks = [b for b in blocks if b.kind in _CHAT_KINDS]
    detail_blocks = [b for b in blocks if b.kind in _DETAIL_KINDS]

    if chat_blocks:
        # Combined / planning: chat = LLM (and errors); KB / MCP in closed drawers.
        for block in chat_blocks:
            if block.kind == "error":
                st.error(block.text.strip())
            else:
                _render_block_body(block)
        for block in detail_blocks:
            title = _EXPANDER_TITLE.get(block.kind, LABEL_PREFIX.get(block.kind, block.kind))
            with st.expander(title, expanded=False):
                _render_block_body(block)
    elif detail_blocks:
        # RAG / weather / FX only — the block *is* the chat reply (no LLM layer).
        for block in detail_blocks:
            _render_block_body(block)
    else:
        st.markdown(content)

    if meta_caption:
        st.caption(meta_caption)


def main() -> None:
    _init_session()

    st.title("Singapore AI Travel Planning Assistant")
    st.caption("Chat-style replies · KB / MCP details in collapsed drawers · LLM provider toggle")

    with st.sidebar:
        st.header("Settings")
        providers = list(list_providers())
        # Put common ones first
        order = ["openai", "gemini", "cursor", "ollama", "fake"]
        providers = [p for p in order if p in providers] + [
            p for p in providers if p not in order
        ]
        current = st.session_state.llm_provider
        idx = providers.index(current) if current in providers else 0
        choice = st.selectbox("LLM provider", providers, index=idx)
        if choice != st.session_state.llm_provider:
            prev = st.session_state.llm_provider
            st.session_state.llm_provider = choice
            bind_context(llm_provider=choice)
            log_event(
                "llm.provider_changed",
                f"{prev} → {choice}",
                llm_provider=choice,
                status="ok",
            )
            if st.session_state.orchestrator is not None:
                st.session_state.orchestrator.set_provider(choice)

        try:
            emb_name = _embedding_provider_for(choice)
        except ConfigError:
            emb_name = (os.getenv("EMBEDDING_PROVIDER") or "unset").strip() or "unset"
        st.caption(f"Embeddings: `{emb_name}` (from `EMBEDDING_PROVIDER` / .env)")

        st.checkbox(
            "MCP mock mode",
            value=(os.getenv("MCP_MOCK_MODE") or "").lower() in {"1", "true", "yes"},
            key="mcp_mock_ui",
            help="Uses documented mock weather/FX when enabled (set MCP_MOCK_MODE in .env for persistence).",
        )
        if st.session_state.get("mcp_mock_ui"):
            os.environ["MCP_MOCK_MODE"] = "true"
        else:
            os.environ["MCP_MOCK_MODE"] = "false"

        sess: SessionState = st.session_state.agent_session
        st.markdown("### Session memory")
        st.write(
            {
                "traveler_type": sess.traveler_type,
                "budget": f"{sess.budget_amount} {sess.budget_currency}"
                if sess.budget_amount is not None
                else None,
                "prefer_indoor": sess.prefer_indoor,
                "interests": sess.interests,
            }
        )
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.session_state.agent_session = SessionState(session_id="ui")
            st.session_state.orchestrator = None
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                _render_assistant_message(
                    content=msg.get("content") or "",
                    blocks=_blocks_from_payload(msg.get("blocks")),
                    meta_caption=msg.get("meta_caption"),
                )
            else:
                st.markdown(msg["content"])

    prompt = st.chat_input("Ask about Singapore travel, weather, or currency…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    answer = ""
    blocks_payload: list[dict[str, Any]] = []
    meta_caption: str | None = None

    with st.chat_message("assistant"):
        try:
            orch = _get_orchestrator(st.session_state.llm_provider)
            # Refresh MCP clients if mock toggled
            mock = st.session_state.get("mcp_mock_ui", False)
            orch.weather = WeatherClient(mock=bool(mock))
            orch.currency = CurrencyClient(mock=bool(mock))
            orch.wx.client = orch.weather
            orch.fx.client = orch.currency
            orch.planner.weather = orch.weather
            orch.planner.currency = orch.currency
            orch.planner._wx.client = orch.weather
            orch.planner._fx.client = orch.currency

            with st.spinner("Thinking…"):
                resp = orch.handle(prompt)

            meta_bits = [f"intent=`{resp.intent}`", f"agent=`{resp.agent}`"]
            if resp.provider:
                meta_bits.append(f"provider=`{resp.provider}`")
            if resp.used_rag:
                meta_bits.append("RAG")
            if resp.used_mcp:
                meta_bits.append("MCP")
            meta_caption = " · ".join(meta_bits)

            answer = resp.answer
            blocks_payload = [
                {
                    "kind": b.kind,
                    "text": b.text,
                    "citations": b.citations,
                    "meta": b.meta,
                }
                for b in resp.blocks
            ]
            _render_assistant_message(
                content=answer,
                blocks=list(resp.blocks),
                meta_caption=meta_caption,
            )
        except ConfigError as exc:
            answer = f"[Error] LLM configuration error: {exc}. No silent fallback."
            meta_caption = None
            blocks_payload = [{"kind": "error", "text": answer, "citations": [], "meta": {}}]
            st.error(answer)
        except Exception as exc:  # noqa: BLE001
            answer = f"[Error] {exc}"
            meta_caption = None
            blocks_payload = [{"kind": "error", "text": answer, "citations": [], "meta": {}}]
            st.error(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "blocks": blocks_payload,
            "meta_caption": meta_caption,
        }
    )
    st.session_state.agent_session = (
        st.session_state.orchestrator.session
        if st.session_state.orchestrator
        else st.session_state.agent_session
    )


if __name__ == "__main__":
    main()
