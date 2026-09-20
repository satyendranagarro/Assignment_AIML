"""Phase 1.5 knowledge IaC — compose units and env contract."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"


def test_infra_layout_exists():
    assert (INFRA / "README.md").is_file()
    assert (INFRA / "compose.yml").is_file()
    assert (INFRA / "neo4j" / "compose.yml").is_file()
    assert (INFRA / "chroma" / "compose.yml").is_file()
    assert (INFRA / "kb-pipeline" / "Dockerfile").is_file()
    assert (INFRA / "kb-pipeline" / "README.md").is_file()


def test_neo4j_compose_defines_service_and_healthcheck():
    data = yaml.safe_load((INFRA / "neo4j" / "compose.yml").read_text(encoding="utf-8"))
    assert "neo4j" in data["services"]
    neo = data["services"]["neo4j"]
    assert "healthcheck" in neo
    assert "7687" in str(neo.get("ports", []))
    assert "neo4j_data" in data.get("volumes", {})


def test_chroma_compose_defines_service_and_healthcheck():
    data = yaml.safe_load((INFRA / "chroma" / "compose.yml").read_text(encoding="utf-8"))
    assert "chroma" in data["services"]
    chroma = data["services"]["chroma"]
    assert "healthcheck" in chroma
    assert "8000" in str(chroma.get("ports", []))
    assert "chroma_data" in data.get("volumes", {})


def test_umbrella_includes_knowledge_units():
    text = (INFRA / "compose.yml").read_text(encoding="utf-8")
    assert "neo4j/compose.yml" in text
    assert "chroma/compose.yml" in text
    assert "kb-pipeline" in text


def test_env_example_documents_knowledge_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "NEO4J_URI" in text
    assert "NEO4J_PASSWORD" in text
    assert "CHROMA_PATH" in text
    assert "CHROMA_HOST" in text
    assert "CHROMA_PORT" in text


def test_chroma_server_settings_respects_env(monkeypatch):
    from src.rag.chroma_store import chroma_server_settings

    monkeypatch.delenv("CHROMA_HOST", raising=False)
    assert chroma_server_settings() is None
    monkeypatch.setenv("CHROMA_HOST", "localhost")
    monkeypatch.setenv("CHROMA_PORT", "8000")
    assert chroma_server_settings() == ("localhost", 8000)
