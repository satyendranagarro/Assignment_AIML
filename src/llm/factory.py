"""Chat + embedding factory — resolves provider and delegates to adapters.

Switch providers with `LLM_PROVIDER` / Streamlit session / explicit kwarg.
Callers should use only `get_chat_model` / `get_embeddings` / `get_adapter`.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from src.llm.adapters import ADAPTERS
from src.llm.contract import (
    VALID_PROVIDERS,
    ConfigError,
    LLMProviderAdapter,
    ProviderName,
)

# Re-export for existing imports
__all__ = [
    "ConfigError",
    "ProviderName",
    "get_adapter",
    "get_chat_model",
    "get_embeddings",
    "list_providers",
    "resolve_embedding_provider",
    "resolve_provider",
]


def _session_provider() -> str | None:
    try:
        import streamlit as st

        val = st.session_state.get("llm_provider")
        return str(val) if val else None
    except Exception:
        return None


def resolve_provider(explicit: str | None = None) -> ProviderName:
    """kwarg → Streamlit session → LLM_PROVIDER env → default openai."""
    load_dotenv()
    raw = (
        explicit or _session_provider() or os.getenv("LLM_PROVIDER") or "openai"
    ).strip().lower()
    if raw == "azure":
        # Back-compat alias: treat Azure OpenAI as openai-compatible via env.
        raw = "openai"
    if raw not in VALID_PROVIDERS:
        raise ConfigError(
            f"Unknown LLM_PROVIDER={raw!r}. Expected one of: "
            + ", ".join(sorted(VALID_PROVIDERS))
        )
    return raw  # type: ignore[return-value]


def resolve_embedding_provider(explicit: str | None = None) -> ProviderName:
    load_dotenv()
    if explicit:
        return resolve_provider(explicit)
    emb = (os.getenv("EMBEDDING_PROVIDER") or "").strip().lower()
    if emb:
        return resolve_provider(emb)
    return resolve_provider(None)


def list_providers() -> tuple[ProviderName, ...]:
    """Registered provider names (for UI toggles / docs)."""
    return tuple(sorted(ADAPTERS.keys()))  # type: ignore[return-value]


def get_adapter(provider: str | None = None) -> LLMProviderAdapter:
    """Instantiate the adapter for the resolved provider (switch point)."""
    name = resolve_provider(provider)
    cls = ADAPTERS.get(name)
    if cls is None:
        raise ConfigError(f"No adapter registered for provider={name!r}")
    return cls()  # type: ignore[operator, return-value]


def get_chat_model(
    provider: str | None = None,
    *,
    temperature: float = 0.2,
    **kwargs: Any,
) -> Any:
    """Return a LangChain chat model for the selected provider."""
    load_dotenv()
    return get_adapter(provider).get_chat_model(temperature=temperature, **kwargs)


def get_embeddings(provider: str | None = None, **kwargs: Any) -> Any:
    """Return a LangChain Embeddings instance for the selected provider."""
    load_dotenv()
    name = resolve_embedding_provider(provider)
    return get_adapter(name).get_embeddings(**kwargs)
