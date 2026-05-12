from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "connectors" / "automotive-security-timeline" / "src" / "main.py"


def test_connector_keeps_single_stable_entry_class() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    assert "AutomotiveSecurityTimelineConnector" in class_names


def test_connector_keeps_runtime_env_boundary_explicit() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    required_markers = [
        "OPENCTI_URL",
        "OPENCTI_TOKEN",
        "CONNECTOR_ID",
        "AUTOMOTIVE_TIMELINE_SOURCE_URL",
        "AUTOMOTIVE_TIMELINE_VERIFY_TLS",
        "AUTOMOTIVE_TIMELINE_REQUEST_TIMEOUT",
    ]
    for marker in required_markers:
        assert marker in text, f"Missing runtime boundary marker: {marker}"