"""Cursor adapter — Cursor SDK (online) or optional OpenAI-compatible gateway.

Online (default when CURSOR_API_KEY is set):
  Uses `cursor-sdk` Agent.prompt against a no-repo cloud agent (or local
  scratch cwd). No local gateway required.

Gateway (optional):
  Set CURSOR_USE_GATEWAY=true and CURSOR_LLM_BASE_URL (e.g. http://localhost:8787/v1)
  to keep the ChatOpenAI path.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from src.llm.contract import ConfigError, ProviderName


class CursorAdapter:
    """Chat via Cursor SDK; embeddings via gateway or ConfigError (use EMBEDDING_PROVIDER)."""

    name: ProviderName = "cursor"

    def _api_key(self) -> str:
        key = (os.getenv("CURSOR_API_KEY") or "").strip()
        if not key:
            raise ConfigError(
                "CURSOR_API_KEY is required when LLM_PROVIDER=cursor "
                "(https://cursor.com/dashboard/integrations)"
            )
        return key

    def _use_gateway(self) -> bool:
        flag = (os.getenv("CURSOR_USE_GATEWAY") or "").strip().lower()
        return flag in {"1", "true", "yes"}

    def get_chat_model(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        if self._use_gateway():
            return self._gateway_chat(temperature=temperature, **kwargs)
        return CursorSDKChatModel(
            api_key=self._api_key(),
            model=os.getenv("CURSOR_MODEL", "composer-2.5"),
            temperature=temperature,
            runtime=(os.getenv("CURSOR_RUNTIME") or "cloud").strip().lower(),
            **{k: v for k, v in kwargs.items() if k in ("runtime",)},
        )

    def _gateway_chat(self, *, temperature: float = 0.2, **kwargs: Any) -> Any:
        api_key = self._api_key()
        base_url = (os.getenv("CURSOR_LLM_BASE_URL") or "").strip().rstrip("/")
        if not base_url:
            raise ConfigError(
                "CURSOR_LLM_BASE_URL is required when CURSOR_USE_GATEWAY=true "
                "(e.g. http://localhost:8787/v1)"
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.getenv("CURSOR_MODEL", "composer-2.5"),
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            **kwargs,
        )

    def get_embeddings(self, **kwargs: Any) -> Any:
        # Cursor agent SDK is not an embeddings API — require gateway or raise.
        if not self._use_gateway():
            raise ConfigError(
                "Cursor SDK does not provide embeddings. Set EMBEDDING_PROVIDER="
                "openai|gemini|fake (recommended) when LLM_PROVIDER=cursor."
            )
        api_key = self._api_key()
        base_url = (os.getenv("CURSOR_LLM_BASE_URL") or "").strip().rstrip("/")
        if not base_url:
            raise ConfigError(
                "CURSOR_LLM_BASE_URL required for Cursor gateway embeddings"
            )
        from langchain_openai import OpenAIEmbeddings

        model = os.getenv(
            "CURSOR_EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        return OpenAIEmbeddings(
            model=model,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )


class CursorSDKChatModel:
    """Minimal LangChain-compatible chat wrapper around cursor_sdk.Agent.prompt."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "composer-2.5",
        temperature: float = 0.2,
        runtime: str = "cloud",
        **_: Any,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.runtime = runtime  # cloud | local

    def invoke(self, messages: Any, **kwargs: Any) -> Any:
        from langchain_core.messages import AIMessage

        text = self._messages_to_prompt(messages)
        reply = self._prompt(text)
        return AIMessage(content=reply)

    def _messages_to_prompt(self, messages: Any) -> str:
        parts: list[str] = [
            "You are answering a chat request for a Singapore travel assistant. "
            "Reply with plain text only. Do not edit files, run shell commands, "
            "or call tools unless absolutely required to answer. "
            "Do not invent destination facts not present in the user message."
        ]
        seq = messages if isinstance(messages, (list, tuple)) else [messages]
        for msg in seq:
            role = getattr(msg, "type", None) or getattr(msg, "role", "user")
            content = getattr(msg, "content", None)
            if content is None:
                content = str(msg)
            if isinstance(content, list):
                content = "".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in content
                )
            parts.append(f"{role.upper()}:\n{content}")
        return "\n\n".join(parts)

    def _prompt(self, text: str) -> str:
        try:
            from cursor_sdk import Agent, AgentOptions, CloudAgentOptions, LocalAgentOptions
        except ImportError as exc:
            raise ConfigError(
                "cursor-sdk is required for online Cursor mode. "
                "Install with: pip install cursor-sdk"
            ) from exc

        options_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "model": self.model,
        }
        if self.runtime == "local":
            scratch = tempfile.mkdtemp(prefix="cursor-chat-")
            options_kwargs["local"] = LocalAgentOptions(cwd=scratch)
        else:
            # No-repo cloud agent — online mode without cloning this repo
            options_kwargs["cloud"] = CloudAgentOptions(repos=[])

        try:
            result = Agent.prompt(text, AgentOptions(**options_kwargs))
        except Exception as exc:  # noqa: BLE001
            # Fall back to local scratch if no-repo cloud is disabled for the key
            if self.runtime != "local" and "repos" in str(exc).lower():
                scratch = tempfile.mkdtemp(prefix="cursor-chat-")
                result = Agent.prompt(
                    text,
                    AgentOptions(
                        api_key=self.api_key,
                        model=self.model,
                        local=LocalAgentOptions(cwd=scratch),
                    ),
                )
            else:
                raise ConfigError(f"Cursor SDK chat failed: {exc}") from exc

        status = getattr(result, "status", None)
        if status == "error":
            raise ConfigError(
                f"Cursor SDK run failed (status=error, id={getattr(result, 'id', '?')})"
            )
        out = getattr(result, "result", None)
        if out is None:
            out = str(result)
        return str(out).strip()
