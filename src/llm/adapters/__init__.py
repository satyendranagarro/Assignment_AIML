"""Provider adapters implementing LLMProviderAdapter."""

from __future__ import annotations

from src.llm.adapters.cursor import CursorAdapter
from src.llm.adapters.fake import FakeAdapter
from src.llm.adapters.gemini import GeminiAdapter
from src.llm.adapters.ollama import OllamaAdapter
from src.llm.adapters.openai_adapter import OpenAIAdapter
from src.llm.contract import LLMProviderAdapter, ProviderName

ADAPTERS: dict[ProviderName, type[LLMProviderAdapter]] = {
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "cursor": CursorAdapter,
    "ollama": OllamaAdapter,
    "fake": FakeAdapter,
}

__all__ = [
    "ADAPTERS",
    "CursorAdapter",
    "FakeAdapter",
    "GeminiAdapter",
    "OllamaAdapter",
    "OpenAIAdapter",
]
