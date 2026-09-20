"""Unit tests for LLM adapter contract + factory switch."""

from __future__ import annotations

import pytest

from src.llm.adapters import ADAPTERS
from src.llm.adapters.cursor import CursorAdapter
from src.llm.adapters.fake import FakeAdapter
from src.llm.contract import ConfigError, LLMProviderAdapter
from src.llm.factory import (
    get_adapter,
    get_chat_model,
    get_embeddings,
    list_providers,
    resolve_provider,
)


def test_all_registered_adapters_satisfy_contract():
    for name, cls in ADAPTERS.items():
        adapter = cls()
        assert isinstance(adapter, LLMProviderAdapter)
        assert adapter.name == name


def test_list_providers_matches_registry():
    assert set(list_providers()) == set(ADAPTERS.keys())


def test_get_adapter_switch(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    adapter = get_adapter()
    assert adapter.name == "fake"
    assert isinstance(adapter, FakeAdapter)


def test_get_adapter_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    adapter = get_adapter("fake")
    assert adapter.name == "fake"


def test_fake_chat_and_embeddings():
    chat = get_chat_model("fake")
    assert chat.invoke("hi").content == "[fake LLM response]"
    emb = get_embeddings("fake")
    vec = emb.embed_query("singapore marina bay")
    assert len(vec) == 384
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6


def test_cursor_adapter_requires_key(monkeypatch):
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("CURSOR_USE_GATEWAY", raising=False)
    adapter = CursorAdapter()
    with pytest.raises(ConfigError, match="CURSOR_API_KEY"):
        adapter.get_chat_model()


def test_cursor_adapter_sdk_chat_model_default(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "test-key")
    monkeypatch.delenv("CURSOR_USE_GATEWAY", raising=False)
    monkeypatch.setenv("CURSOR_MODEL", "composer-2.5")
    adapter = CursorAdapter()
    model = adapter.get_chat_model(temperature=0.1)
    from src.llm.adapters.cursor import CursorSDKChatModel

    assert isinstance(model, CursorSDKChatModel)
    assert model.model == "composer-2.5"


def test_cursor_adapter_builds_chat_with_gateway(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "test-key")
    monkeypatch.setenv("CURSOR_USE_GATEWAY", "true")
    monkeypatch.setenv("CURSOR_LLM_BASE_URL", "http://localhost:8787/v1/")
    monkeypatch.setenv("CURSOR_MODEL", "composer-2.5")
    adapter = CursorAdapter()
    model = adapter.get_chat_model(temperature=0.1)
    # LangChain ChatOpenAI stores these on the client / model fields
    assert getattr(model, "model_name", None) or getattr(model, "model", None)
    assert "8787" in str(getattr(model, "openai_api_base", None) or model.client)


def test_cursor_embeddings_require_override_without_gateway(monkeypatch):
    monkeypatch.setenv("CURSOR_API_KEY", "test-key")
    monkeypatch.delenv("CURSOR_USE_GATEWAY", raising=False)
    adapter = CursorAdapter()
    with pytest.raises(ConfigError, match="EMBEDDING_PROVIDER"):
        adapter.get_embeddings()


def test_ollama_adapter_unreachable(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9")
    from src.llm.adapters.ollama import OllamaAdapter

    adapter = OllamaAdapter()
    with pytest.raises(ConfigError, match="Ollama is not reachable"):
        adapter.get_embeddings()


def test_resolve_provider_rejects_unknown(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ConfigError, match="Unknown LLM_PROVIDER"):
        resolve_provider()


def test_azure_alias_maps_to_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    assert resolve_provider() == "openai"
