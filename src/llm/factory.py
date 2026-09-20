"""Chat + embedding factory with toggleable providers (no silent fallback)."""

from __future__ import annotations

import os
from typing import Any, Literal

from dotenv import load_dotenv

ProviderName = Literal["openai", "gemini", "cursor", "fake"]

_VALID = frozenset({"openai", "gemini", "cursor", "fake"})


class ConfigError(RuntimeError):
    """Selected provider is missing required configuration."""


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
    raw = (explicit or _session_provider() or os.getenv("LLM_PROVIDER") or "openai").strip().lower()
    if raw == "azure":
        # Back-compat alias: treat Azure OpenAI as openai-compatible via env.
        raw = "openai"
    if raw not in _VALID:
        raise ConfigError(
            f"Unknown LLM_PROVIDER={raw!r}. Expected one of: openai, gemini, cursor, fake"
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


def get_chat_model(
    provider: str | None = None,
    *,
    temperature: float = 0.2,
    **kwargs: Any,
) -> Any:
    """Return a LangChain chat model for the selected provider."""
    name = resolve_provider(provider)
    load_dotenv()

    if name == "fake":
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        return FakeListChatModel(responses=kwargs.get("responses") or ["[fake LLM response]"])

    if name == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        # Azure OpenAI path when endpoint + deployment are set
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        if endpoint and deployment:
            from langchain_openai import AzureChatOpenAI

            return AzureChatOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                azure_deployment=deployment,
                temperature=temperature,
                **kwargs,
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )

    if name == "gemini":
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

    # cursor — OpenAI-compatible gateway
    api_key = os.getenv("CURSOR_API_KEY")
    base_url = os.getenv("CURSOR_LLM_BASE_URL")
    if not api_key or not base_url:
        raise ConfigError(
            "CURSOR_API_KEY and CURSOR_LLM_BASE_URL are required when LLM_PROVIDER=cursor"
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("CURSOR_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        **kwargs,
    )


def get_embeddings(provider: str | None = None, **kwargs: Any) -> Any:
    """Return a LangChain Embeddings instance for the selected provider."""
    name = resolve_embedding_provider(provider)
    load_dotenv()

    if name == "fake":
        from src.llm.lexical import LexicalHashEmbeddings

        return LexicalHashEmbeddings(size=int(kwargs.get("size", 384)))

    if name == "openai":
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY is required for embeddings (openai)")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        if endpoint and deployment:
            from langchain_openai import AzureOpenAIEmbeddings

            return AzureOpenAIEmbeddings(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                azure_deployment=deployment,
                **kwargs,
            )
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            api_key=api_key,
            **kwargs,
        )

    if name == "gemini":
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
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"),
            google_api_key=api_key,
            **kwargs,
        )

    # cursor — OpenAI-compatible embeddings endpoint
    api_key = os.getenv("CURSOR_API_KEY")
    base_url = os.getenv("CURSOR_LLM_BASE_URL")
    if not api_key or not base_url:
        raise ConfigError(
            "CURSOR_API_KEY and CURSOR_LLM_BASE_URL are required for embeddings (cursor)"
        )
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=os.getenv("CURSOR_EMBEDDING_MODEL", os.getenv("CURSOR_MODEL", "text-embedding-3-small")),
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )
