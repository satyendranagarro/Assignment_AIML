"""Cursor adapter — OpenAI-compatible client against a local Cursor gateway.

Cursor does not expose an official /v1/chat/completions API. Point
CURSOR_LLM_BASE_URL at a gateway that wraps the Cursor SDK (e.g.
http://localhost:8787/v1) and authenticate with CURSOR_API_KEY.
"""

from __future__ import annotations

import os
from typing import Any

from src.llm.contract import ConfigError, ProviderName


class CursorAdapter:
    """LangChain ChatOpenAI / OpenAIEmbeddings via Cursor gateway credentials."""

    name: ProviderName = "cursor"

    def _require_gateway(self) -> tuple[str, str]:
        api_key = (os.getenv("CURSOR_API_KEY") or "").strip()
        base_url = (os.getenv("CURSOR_LLM_BASE_URL") or "").strip().rstrip("/")
        if not api_key or not base_url:
            raise ConfigError(
                "CURSOR_API_KEY and CURSOR_LLM_BASE_URL are required when "
                "LLM_PROVIDER=cursor (OpenAI-compatible gateway, e.g. "
                "http://localhost:8787/v1)"
            )
        return api_key, base_url

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        api_key, base_url = self._require_gateway()
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("CURSOR_MODEL", "composer-2.5"),
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

    def get_embeddings(self, **kwargs: Any) -> Any:
        api_key, base_url = self._require_gateway()
        from langchain_openai import OpenAIEmbeddings

        model = os.getenv(
            "CURSOR_EMBEDDING_MODEL",
            os.getenv("CURSOR_MODEL", "text-embedding-3-small"),
        )
        return OpenAIEmbeddings(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
