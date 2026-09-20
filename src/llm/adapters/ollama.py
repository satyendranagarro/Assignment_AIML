"""Local Ollama adapter (chat + embeddings via localhost)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urljoin

import httpx

from src.llm.contract import ConfigError, ProviderName


def _base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")


def _ensure_reachable(base: str) -> None:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(urljoin(base + "/", "api/tags"))
            resp.raise_for_status()
    except Exception as exc:
        raise ConfigError(
            f"Ollama is not reachable at {base}. Start it (`ollama serve`) "
            "or set OLLAMA_BASE_URL."
        ) from exc


class OllamaAdapter:
    name: ProviderName = "ollama"

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        base = _base_url()
        _ensure_reachable(base)
        model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise ConfigError(
                "langchain-ollama is required for LLM_PROVIDER=ollama"
            ) from exc
        return ChatOllama(
            model=model,
            base_url=base,
            temperature=temperature,
            **kwargs,
        )

    def get_embeddings(self, **kwargs: Any) -> Any:
        base = _base_url()
        _ensure_reachable(base)
        model = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError as exc:
            raise ConfigError(
                "langchain-ollama is required for EMBEDDING_PROVIDER=ollama"
            ) from exc
        return OllamaEmbeddings(
            model=model,
            base_url=base,
            **kwargs,
        )
