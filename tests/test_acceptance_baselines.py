from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_GRAPH = ROOT / "design" / "KG" / "SystemArchitecture.json"
ROOT_CONTRACT = ROOT / "OVERALL_ARCHITECTURE.md"
CONNECTOR_ACCEPTANCE_FILE = ROOT / "tests" / "test_architecture_connector_support.py"
MIRROR_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_neo4j_sync_integrity.py"
MIRROR_BOOTSTRAP_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_bootstrap_window_acceptance.py"
MIRROR_LIVE_INCREMENTAL_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_live_incremental_acceptance.py"
MIRROR_PROJECTION_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_projection_policy_acceptance.py"
MIRROR_RECONCILE_ACCEPTANCE_FILE = ROOT / "tests" / "mirror" / "test_reconcile_acceptance.py"
MIRROR_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "manual_seed_steps.md"
MIRROR_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "cypher_assertions.md"
MIRROR_BOOTSTRAP_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "bootstrap_window_probe.md"
MIRROR_BOOTSTRAP_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "bootstrap_window_contract.md"
MIRROR_LIVE_INCREMENTAL_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "live_incremental_probe.md"
MIRROR_LIVE_INCREMENTAL_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "live_incremental_contract.md"
MIRROR_PROJECTION_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "projection_policy_probe.md"
MIRROR_PROJECTION_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "projection_policy_contract.md"
MIRROR_RECONCILE_FIXTURE_FILE = ROOT / "tests" / "mirror" / "protected_fixtures" / "reconcile_probe.md"
MIRROR_RECONCILE_BASELINE_FILE = ROOT / "tests" / "mirror" / "protected_baselines" / "reconcile_contract.md"
QUERY_BACKEND_ACCEPTANCE_FILE = ROOT / "tests" / "query_backend" / "test_query_backend_acceptance.py"
QUERY_BACKEND_DOCKER_ACCEPTANCE_FILE = ROOT / "tests" / "query_backend" / "test_query_backend_docker_acceptance.py"
FULL_SCOPE_INTROSPECTION_ACCEPTANCE_FILE = ROOT / "tests" / "test_full_scope_introspection_acceptance.py"
QUERY_BACKEND_FIXTURE_FILE = ROOT / "tests" / "query_backend" / "protected_fixtures" / "rejected_cypher_and_degraded_probe.md"
QUERY_BACKEND_DOCKER_FIXTURE_FILE = ROOT / "tests" / "query_backend" / "protected_fixtures" / "docker_proxy_probe.md"
QUERY_BACKEND_BASELINE_FILE = ROOT / "tests" / "query_backend" / "protected_baselines" / "response_contract.md"
QUERY_BACKEND_DOCKER_BASELINE_FILE = ROOT / "tests" / "query_backend" / "protected_baselines" / "docker_proxy_contract.md"


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
    acceptance = mirror_case["acceptance"]
    match = re.search(
        r"(?P<path>(?:OPENCTI-TEST/)?tests/mirror/test_neo4j_sync_integrity\.py)",
        description,
    )
    assert match, "Mirror testcase must declare its physical test file in the architecture graph"
    assert acceptance == "tests/mirror/test_neo4j_sync_integrity.py::test_neo4j_sync_integrity"
    assert MIRROR_ACCEPTANCE_FILE.is_file(), "Mirror acceptance entry file is missing"
    assert "test_neo4j_sync_integrity" in _load_test_function_names(MIRROR_ACCEPTANCE_FILE)


def test_new_mirror_acceptance_entries_are_physicalized() -> None:
    cases = _collect_testcases()
    bootstrap_case = cases["近一年窗口热子图初始化同步"]
    two_hop_case = cases["二跳邻域补齐完整性"]
    live_case = cases["Live Stream 增量实时同步"]
    replay_case = cases["Watermark 恢复后幂等补偿"]
    projection_case = cases["属性名称与默认基线投影一致性"]
    reconcile_case = cases["删除与撤销状态对齐"]

    assert bootstrap_case["acceptance"] == (
        "tests/mirror/test_bootstrap_window_acceptance.py::"
        "test_default_one_year_window_syncs_changed_hot_subgraph"
    )
    assert two_hop_case["acceptance"] == (
        "tests/mirror/test_bootstrap_window_acceptance.py::"
        "test_two_hop_neighborhood_completion_preserves_direction"
    )
    assert live_case["acceptance"] == (
        "tests/mirror/test_live_incremental_acceptance.py::"
        "test_live_stream_updates_reach_replica_and_refresh_freshness"
    )
    assert replay_case["acceptance"] == (
        "tests/mirror/test_live_incremental_acceptance.py::"
        "test_watermark_recovery_replays_idempotently"
    )
    assert projection_case["acceptance"] == (
        "tests/mirror/test_projection_policy_acceptance.py::"
        "test_property_names_and_default_baseline_are_preserved"
    )
    assert reconcile_case["acceptance"] == (
        "tests/mirror/test_reconcile_acceptance.py::"
        "test_delete_and_revoke_semantics_align_in_replica"
    )

    assert MIRROR_BOOTSTRAP_ACCEPTANCE_FILE.is_file(), "Mirror bootstrap acceptance entry file is missing"
    assert MIRROR_LIVE_INCREMENTAL_ACCEPTANCE_FILE.is_file(), "Mirror live incremental acceptance entry file is missing"
    assert MIRROR_PROJECTION_ACCEPTANCE_FILE.is_file(), "Mirror projection acceptance entry file is missing"
    assert MIRROR_RECONCILE_ACCEPTANCE_FILE.is_file(), "Mirror reconcile acceptance entry file is missing"

    bootstrap_names = _load_test_function_names(MIRROR_BOOTSTRAP_ACCEPTANCE_FILE)
    assert "test_default_one_year_window_syncs_changed_hot_subgraph" in bootstrap_names
    assert "test_two_hop_neighborhood_completion_preserves_direction" in bootstrap_names

    incremental_names = _load_test_function_names(MIRROR_LIVE_INCREMENTAL_ACCEPTANCE_FILE)
    assert "test_live_stream_updates_reach_replica_and_refresh_freshness" in incremental_names
    assert "test_watermark_recovery_replays_idempotently" in incremental_names

    projection_names = _load_test_function_names(MIRROR_PROJECTION_ACCEPTANCE_FILE)
    assert "test_property_names_and_default_baseline_are_preserved" in projection_names

    reconcile_names = _load_test_function_names(MIRROR_RECONCILE_ACCEPTANCE_FILE)
    assert "test_delete_and_revoke_semantics_align_in_replica" in reconcile_names


def test_full_scope_introspection_acceptance_entry_is_physicalized() -> None:
    cases = _collect_testcases()
    scope_case = cases["OpenCTI 平台全量元素关系属性覆盖盘点"]

    assert scope_case["description"], "Full scope introspection testcase must remain declared in the architecture graph"
    assert scope_case["acceptance"] == (
        "tests/test_full_scope_introspection_acceptance.py::"
        "test_full_scope_introspection_covers_live_opencti_schema"
    )
    assert FULL_SCOPE_INTROSPECTION_ACCEPTANCE_FILE.is_file(), "Full scope introspection acceptance entry file is missing"

    function_names = _load_test_function_names(FULL_SCOPE_INTROSPECTION_ACCEPTANCE_FILE)
    assert "test_full_scope_introspection_covers_live_opencti_schema" in function_names


def test_mirror_protected_fixture_and_baseline_files_exist() -> None:
    assert MIRROR_FIXTURE_FILE.is_file(), "Mirror protected fixture file is missing"
    assert MIRROR_BASELINE_FILE.is_file(), "Mirror protected baseline file is missing"
    assert MIRROR_BOOTSTRAP_FIXTURE_FILE.is_file(), "Mirror bootstrap protected fixture file is missing"
    assert MIRROR_BOOTSTRAP_BASELINE_FILE.is_file(), "Mirror bootstrap protected baseline file is missing"
    assert MIRROR_LIVE_INCREMENTAL_FIXTURE_FILE.is_file(), "Mirror live incremental protected fixture file is missing"
    assert MIRROR_LIVE_INCREMENTAL_BASELINE_FILE.is_file(), "Mirror live incremental protected baseline file is missing"
    assert MIRROR_PROJECTION_FIXTURE_FILE.is_file(), "Mirror projection protected fixture file is missing"
    assert MIRROR_PROJECTION_BASELINE_FILE.is_file(), "Mirror projection protected baseline file is missing"
    assert MIRROR_RECONCILE_FIXTURE_FILE.is_file(), "Mirror reconcile protected fixture file is missing"
    assert MIRROR_RECONCILE_BASELINE_FILE.is_file(), "Mirror reconcile protected baseline file is missing"


def test_query_backend_acceptance_entries_are_physicalized() -> None:
    cases = _collect_testcases()
    controlled_rejection_case = cases["受控 Cypher 拒绝与结构化反馈"]
    degraded_case = cases["副本降级不静默回退"]
    docker_case = cases["Docker统一代理查询入口可用性验证"]
    root_contract_text = ROOT_CONTRACT.read_text(encoding="utf-8")

    assert controlled_rejection_case["description"], "Controlled Cypher rejection testcase must remain declared in the architecture graph"
    assert degraded_case["description"], "Replica degradation testcase must remain declared in the architecture graph"
    assert docker_case["description"], "Docker proxy testcase must remain declared in the architecture graph"
    assert controlled_rejection_case["acceptance"] == (
        "tests/query_backend/test_query_backend_acceptance.py::"
        "test_controlled_cypher_rejection_returns_structured_feedback"
    )
    assert degraded_case["acceptance"] == (
        "tests/query_backend/test_query_backend_acceptance.py::"
        "test_replica_degradation_does_not_fall_back_silently"
    )
    assert docker_case["acceptance"] == (
        "tests/query_backend/test_query_backend_docker_acceptance.py::"
        "test_docker_proxy_entry_preserves_structured_rejection_contract"
    )
    assert "受控 Cypher 拒绝与结构化反馈" in root_contract_text
    assert "副本降级不静默回退" in root_contract_text
    assert "tests/query_backend/test_query_backend_acceptance.py" in root_contract_text
    assert "Docker统一代理查询入口可用性验证" in root_contract_text
    assert "tests/query_backend/test_query_backend_docker_acceptance.py" in root_contract_text
    assert QUERY_BACKEND_ACCEPTANCE_FILE.is_file(), "Query backend acceptance entry file is missing"
    assert QUERY_BACKEND_DOCKER_ACCEPTANCE_FILE.is_file(), "Query backend docker acceptance entry file is missing"

    function_names = _load_test_function_names(QUERY_BACKEND_ACCEPTANCE_FILE)
    assert "test_successful_query_returns_graph_payload_and_freshness_metadata" in function_names
    assert "test_controlled_cypher_rejection_returns_structured_feedback" in function_names
    assert "test_replica_degradation_does_not_fall_back_silently" in function_names

    docker_function_names = _load_test_function_names(QUERY_BACKEND_DOCKER_ACCEPTANCE_FILE)
    assert "test_docker_proxy_entry_preserves_structured_rejection_contract" in docker_function_names


def test_query_backend_protected_fixture_and_baseline_files_exist() -> None:
    assert QUERY_BACKEND_FIXTURE_FILE.is_file(), "Query backend protected fixture file is missing"
    assert QUERY_BACKEND_BASELINE_FILE.is_file(), "Query backend protected baseline file is missing"
    assert QUERY_BACKEND_DOCKER_FIXTURE_FILE.is_file(), "Query backend docker protected fixture file is missing"
    assert QUERY_BACKEND_DOCKER_BASELINE_FILE.is_file(), "Query backend docker protected baseline file is missing"