"""Phase 6 ops IaC — MCP/app compose units, umbrella profiles, deliverables."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
DOCS = ROOT / "docs"


def test_phase6_infra_layout():
    assert (INFRA / "mcp-weather" / "compose.yml").is_file()
    assert (INFRA / "mcp-weather" / "Dockerfile").is_file()
    assert (INFRA / "mcp-currency" / "compose.yml").is_file()
    assert (INFRA / "mcp-currency" / "Dockerfile").is_file()
    assert (INFRA / "app" / "compose.yml").is_file()
    assert (INFRA / "app" / "Dockerfile").is_file()
    assert (INFRA / "mcp-weather" / "README.md").is_file()
    assert (INFRA / "mcp-currency" / "README.md").is_file()
    assert (INFRA / "app" / "README.md").is_file()


def test_mcp_weather_compose_profile_and_health():
    data = yaml.safe_load((INFRA / "mcp-weather" / "compose.yml").read_text(encoding="utf-8"))
    svc = data["services"]["mcp-weather"]
    assert "mcp" in svc.get("profiles", [])
    assert "healthcheck" in svc
    assert "Dockerfile" in str(svc.get("build", {}))


def test_mcp_currency_compose_profile_and_health():
    data = yaml.safe_load((INFRA / "mcp-currency" / "compose.yml").read_text(encoding="utf-8"))
    svc = data["services"]["mcp-currency"]
    assert "mcp" in svc.get("profiles", [])
    assert "healthcheck" in svc


def test_app_compose_profile_port_and_health():
    data = yaml.safe_load((INFRA / "app" / "compose.yml").read_text(encoding="utf-8"))
    svc = data["services"]["app"]
    assert "app" in svc.get("profiles", [])
    assert "8501" in str(svc.get("ports", []))
    assert "healthcheck" in svc


def test_umbrella_includes_runtime_units_and_profiles():
    text = (INFRA / "compose.yml").read_text(encoding="utf-8")
    assert "mcp-weather/compose.yml" in text
    assert "mcp-currency/compose.yml" in text
    assert "app/compose.yml" in text
    assert "neo4j/compose.yml" in text
    assert "chroma/compose.yml" in text
    assert "profile" in text.lower()


def test_deliverable_docs_exist():
    assert (DOCS / "DEMO_CHECKLIST.md").is_file()
    assert (DOCS / "SAMPLE_QA.md").is_file()
    assert (DOCS / "architecture" / "06-ops-and-acceptance.md").is_file()
    demo = (DOCS / "DEMO_CHECKLIST.md").read_text(encoding="utf-8")
    assert "UC-COMBO-01" in demo or "streamlit" in demo.lower()
    sample = (DOCS / "SAMPLE_QA.md").read_text(encoding="utf-8")
    assert "[KB fact]" in sample
    assert "[MCP data]" in sample


def test_env_example_documents_runtime_vars():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "MCP_MOCK_MODE" in text
    assert "WEATHER_MCP_URL" in text
    assert "CURRENCY_MCP_URL" in text
    assert "LOG_LEVEL" in text


def test_readme_documents_full_demo_path():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "infra/compose.yml" in text
    assert "streamlit" in text.lower()
    assert "DEMO_CHECKLIST" in text or "Sample" in text or "SAMPLE_QA" in text
