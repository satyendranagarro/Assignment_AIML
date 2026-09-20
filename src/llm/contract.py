"""Common LLM provider contract — adapters implement this; callers use the factory."""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

ProviderName = Literal["openai", "gemini", "cursor", "fake"]

VALID_PROVIDERS: frozenset[str] = frozenset({"openai", "gemini", "cursor", "fake"})


class ConfigError(RuntimeError):
    """Selected provider is missing required configuration."""


@runtime_checkable
class LLMProviderAdapter(Protocol):
    """Uniform surface for chat + embeddings across providers.

    Factory resolves a provider name and delegates here so switching is
    `LLM_PROVIDER=<name>` (or an explicit kwarg / Streamlit session) only.
    """

    name: ProviderName

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        """Return a LangChain chat model for this provider."""
        ...

    def get_embeddings(self, **kwargs: Any) -> Any:
        """Return a LangChain Embeddings instance for this provider."""
        ...
