"""Offline fake adapter for tests (no API keys)."""

from __future__ import annotations

from typing import Any

from src.llm.contract import ProviderName


class FakeAdapter:
    name: ProviderName = "fake"

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(
            responses=kwargs.get("responses") or ["[fake LLM response]"]
        )

    def get_embeddings(self, **kwargs: Any) -> Any:
        from src.llm.lexical import LexicalHashEmbeddings

        return LexicalHashEmbeddings(size=int(kwargs.get("size", 384)))
