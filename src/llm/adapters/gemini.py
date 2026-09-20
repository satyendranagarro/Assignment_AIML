"""Google Gemini adapter."""

from __future__ import annotations

import os
from typing import Any

from src.llm.contract import ConfigError, ProviderName


class GeminiAdapter:
    name: ProviderName = "gemini"

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ConfigError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ConfigError(
                "langchain-google-genai is required for LLM_PROVIDER=gemini"
            ) from exc
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            google_api_key=api_key,
            temperature=temperature,
            **kwargs,
        )

    def get_embeddings(self, **kwargs: Any) -> Any:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ConfigError("GOOGLE_API_KEY is required for embeddings (gemini)")
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as exc:
            raise ConfigError(
                "langchain-google-genai is required for EMBEDDING_PROVIDER=gemini"
            ) from exc
        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
            google_api_key=api_key,
            **kwargs,
        )
