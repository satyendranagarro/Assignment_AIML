"""LLM / embedding factory (provider toggle via adapters)."""

from src.llm.contract import ConfigError, LLMProviderAdapter, ProviderName
from src.llm.factory import (
    get_adapter,
    get_chat_model,
    get_embeddings,
    list_providers,
    resolve_embedding_provider,
    resolve_provider,
)

__all__ = [
    "ConfigError",
    "LLMProviderAdapter",
    "ProviderName",
    "get_adapter",
    "get_chat_model",
    "get_embeddings",
    "list_providers",
    "resolve_embedding_provider",
    "resolve_provider",
]
