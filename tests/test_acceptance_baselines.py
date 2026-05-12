from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_GRAPH = ROOT / "design" / "KG" / "SystemArchitecture.json"
CONNECTOR_ACCEPTANCE_FILE = ROOT / "tests" / "test_architecture_connector_support.py"
MIRROR_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_neo4j_sync_integrity.py"
MIRROR_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "manual_seed_steps.md"
MIRROR_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "cypher_assertions.md"


def _load_graph() -> dict:
    return json.loads(ARCHITECTURE_GRAPH.read_text(encoding="utf-8"))


def _collect_testcases() -> dict[str, dict]:
    graph = _load_graph()
    cases: dict[str, dict] = {}
    for element in graph.get("elements", []):
        for testcase in element.get("testcases", []):
            cases[testcase["name"]] = {
                "acceptance": testcase.get("acceptanceCriteria", ""),
                "description": testcase.get("description", ""),
            }
    return cases


def _load_test_function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


def test_connector_acceptance_cases_stay_on_single_readonly_entry() -> None:
    cases = _collect_testcases()
    connector_cases = {
        name: payload
        for name, payload in cases.items()
        if payload["acceptance"].startswith("tests/test_architecture_connector_support.py::")
    }
    assert connector_cases, "Expected connector acceptance cases to remain on the shared connector entry"

    function_names = _load_test_function_names(CONNECTOR_ACCEPTANCE_FILE)
    for payload in connector_cases.values():
        _, function_name = payload["acceptance"].split("::", 1)
        assert function_name in function_names, f"Missing acceptance function {function_name}"


def test_mirror_acceptance_entry_is_physicalized() -> None:
    cases = _collect_testcases()
    mirror_case = cases["OpenCTI 情报数据镜像至 Neo4j 完整性验证"]
    description = mirror_case["description"]
    match = re.search(
        r"(?P<path>(?:OPENCTI-TEST/)?tests/mirror/test_neo4j_sync_integrity\.py)",
        description,
    )
    assert match, "Mirror testcase must declare its physical test file in the architecture graph"
    assert MIRROR_ACCEPTANCE_FILE.is_file(), "Mirror acceptance entry file is missing"
    assert "test_neo4j_sync_integrity" in _load_test_function_names(MIRROR_ACCEPTANCE_FILE)


def test_mirror_protected_fixture_and_baseline_files_exist() -> None:
    assert MIRROR_FIXTURE_FILE.is_file(), "Mirror protected fixture file is missing"
    assert MIRROR_BASELINE_FILE.is_file(), "Mirror protected baseline file is missing"