from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_SOURCE = ROOT / "connectors" / "automotive-security-timeline" / "src" / "main.py"
SCRIPTS_DIR = ROOT / "scripts"
MIRROR_SYNC_CONTRACT = ROOT / "mirror-sync" / "ARCHITECTURE.md"
QUERY_BACKEND_CONTRACT = ROOT / "query-backend" / "ARCHITECTURE.md"
DOCKER_COMPOSE_FILE = ROOT / "docker-compose.yml"


def test_custom_connector_does_not_import_repo_internal_layers() -> None:
    tree = ast.parse(CONNECTOR_SOURCE.read_text(encoding="utf-8"))
    import_roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            import_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            import_roots.add(node.module.split(".", 1)[0])

    disallowed = {"tests", "scripts"}
    assert disallowed.isdisjoint(import_roots), f"Connector source must not depend on repo internal layers: {import_roots}"


def test_scripts_do_not_reference_connector_or_pytest_internals() -> None:
    disallowed_markers = [
        "connectors/automotive-security-timeline/src",
        "connectors\\automotive-security-timeline\\src",
        "tests/test_architecture_connector_support.py",
        "tests\\test_architecture_connector_support.py",
        "pytest",
    ]

    for script_path in SCRIPTS_DIR.glob("*.ps1"):
        text = script_path.read_text(encoding="utf-8")
        for marker in disallowed_markers:
            assert marker not in text, f"{script_path} must not depend on {marker}"


def test_mirror_acceptance_entry_uses_local_protected_paths() -> None:
    mirror_test_path = ROOT / "tests" / "mirror" / "test_neo4j_sync_integrity.py"
    text = mirror_test_path.read_text(encoding="utf-8")
    assert "protected_fixtures" in text
    assert "protected_baselines" in text


def test_query_backend_acceptance_entry_uses_local_protected_paths() -> None:
    query_backend_test_path = ROOT / "tests" / "query_backend" / "test_query_backend_acceptance.py"
    text = query_backend_test_path.read_text(encoding="utf-8")
    assert "protected_fixtures" in text
    assert "protected_baselines" in text


def test_query_backend_contract_forbids_direct_opencti_fallback_dependency() -> None:
    text = QUERY_BACKEND_CONTRACT.read_text(encoding="utf-8")
    assert "不得直接依赖 OpenCTI" in text
    assert "不得静默回退到 GraphQL" in text


def test_query_backend_compose_delivery_uses_neo4j_without_caddy_or_opencti_hops() -> None:
    text = DOCKER_COMPOSE_FILE.read_text(encoding="utf-8")
    query_backend_section = text.split("  query-backend:\n", 1)[1].split("  opencti:\n", 1)[0]
    assert "NEO4J_MIRROR_HTTP_HOST=neo4j" in query_backend_section
    assert "NEO4J_MIRROR_HTTP_PORT=7474" in query_backend_section
    assert "QUERY_BACKEND_HOST=0.0.0.0" in query_backend_section
    assert "QUERY_BACKEND_PORT=8088" in query_backend_section
    assert "OPENCTI_URL" not in query_backend_section


def test_caddy_exposes_query_backend_as_unified_external_entry() -> None:
    text = (ROOT / "Caddyfile").read_text(encoding="utf-8")
    assert "https://localhost" in text
    assert "path /graph/query" in text
    assert "query-backend:8088" in text


def test_mirror_sync_contract_keeps_opencti_ingress_separate_from_query_backend() -> None:
    text = MIRROR_SYNC_CONTRACT.read_text(encoding="utf-8")
    assert "OpenCTI" in text
    assert "不得向 `query-backend/` 暴露 Agent 查询接口" in text