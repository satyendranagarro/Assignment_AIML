"""OpenAI / Azure OpenAI adapter."""

from __future__ import annotations

import os
from typing import Any

from src.llm.contract import ConfigError, ProviderName


class OpenAIAdapter:
    name: ProviderName = "openai"

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

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

    def get_embeddings(self, **kwargs: Any) -> Any:
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
