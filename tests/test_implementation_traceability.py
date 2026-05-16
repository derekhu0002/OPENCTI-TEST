from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_CONTRACT = ROOT / "OVERALL_ARCHITECTURE.md"
MIRROR_SYNC_CONTRACT = ROOT / "mirror-sync" / "ARCHITECTURE.md"
TESTS_CONTRACT = ROOT / "tests" / "ARCHITECTURE.md"
MIRROR_TEST_CONTRACT = ROOT / "tests" / "mirror" / "ARCHITECTURE.md"
QUERY_BACKEND_CONTRACT = ROOT / "query-backend" / "ARCHITECTURE.md"
QUERY_BACKEND_TEST_CONTRACT = ROOT / "tests" / "query_backend" / "ARCHITECTURE.md"


def test_root_contract_declares_replica_traceability_chain() -> None:
    text = ROOT_CONTRACT.read_text(encoding="utf-8")
    assert "OpenCTIToNeo4jMirrorSync" in text
    assert "mirror-sync/" in text
    assert "test_full_scope_introspection_acceptance.py" in text
    assert "OpenCTI 平台全量元素关系属性覆盖盘点" in text
    assert "test_bootstrap_window_acceptance.py" in text
    assert "test_live_incremental_acceptance.py" in text
    assert "test_projection_policy_acceptance.py" in text
    assert "test_reconcile_acceptance.py" in text
    assert "ReplicaGraphQueryBackend" in text
    assert "query-backend/" in text
    assert "AIAgentGraphInvestigation" in text
    assert "运行时平台通过 `docker-compose.yml` 中的 `query-backend` 独立容器服务" in text


def test_root_contract_declares_query_backend_acceptance_entries() -> None:
    text = ROOT_CONTRACT.read_text(encoding="utf-8")
    assert "test_successful_query_returns_graph_payload_and_freshness_metadata" in text
    assert "受控 Cypher 拒绝与结构化反馈" in text
    assert "副本降级不静默回退" in text
    assert "Docker统一代理查询入口可用性验证" in text
    assert "tests/query_backend/test_query_backend_acceptance.py::test_controlled_cypher_rejection_returns_structured_feedback" in text
    assert "tests/query_backend/test_query_backend_acceptance.py::test_replica_degradation_does_not_fall_back_silently" in text
    assert "tests/query_backend/test_query_backend_docker_acceptance.py::test_docker_proxy_entry_preserves_structured_rejection_contract" in text


def test_local_contracts_keep_direct_implements_relationships() -> None:
    mirror_text = MIRROR_SYNC_CONTRACT.read_text(encoding="utf-8")
    tests_text = TESTS_CONTRACT.read_text(encoding="utf-8")
    mirror_test_text = MIRROR_TEST_CONTRACT.read_text(encoding="utf-8")
    backend_text = QUERY_BACKEND_CONTRACT.read_text(encoding="utf-8")
    test_text = QUERY_BACKEND_TEST_CONTRACT.read_text(encoding="utf-8")

    assert "直接 implements `OpenCTIToNeo4jMirrorSync`" in mirror_text
    assert "OpenCTI 平台全量元素关系属性覆盖盘点" in mirror_text
    assert "直接 implements `ReplicaGraphQueryBackend`" in backend_text
    assert "直接 implements `AIAgentGraphInvestigation`" in backend_text
    assert "Dockerfile" in backend_text
    assert "test_full_scope_introspection_acceptance.py" in tests_text
    assert "直接 implements `OpenCTI 平台全量元素关系属性覆盖盘点`" in tests_text
    assert "近一年窗口热子图初始化同步" in mirror_test_text
    assert "二跳邻域补齐完整性" in mirror_test_text
    assert "Live Stream 增量实时同步" in mirror_test_text
    assert "Watermark 恢复后幂等补偿" in mirror_test_text
    assert "属性名称与默认基线投影一致性" in mirror_test_text
    assert "删除与撤销状态对齐" in mirror_test_text
    assert "test_successful_query_returns_graph_payload_and_freshness_metadata" in test_text
    assert "直接 implements `受控 Cypher 拒绝与结构化反馈`" in test_text
    assert "直接 implements `副本降级不静默回退`" in test_text
    assert "直接 implements `Docker统一代理查询入口可用性验证`" in test_text


def test_sync_scope_declares_explicit_agent_driven_node_scope_union() -> None:
    payload = json.loads((ROOT / "mirror-sync" / "sync_scope.json").read_text(encoding="utf-8"))

    assert payload["enable_all_candidate_node_scopes"] is False

    enabled_node_scopes = {
        str(scope["name"])
        for scope in payload["node_scopes"]
        if isinstance(scope, dict) and scope.get("enabled") is True
    }

    assert {
        "ipv4_observable",
        "domain_name_observable",
        "url_observable",
        "file_observable",
        "indicator",
        "malware",
        "vulnerability",
        "attackPatterns",
        "campaigns",
        "infrastructures",
        "intrusionSets",
        "reports",
        "groupings",
        "identities",
        "sectors",
        "coursesOfAction",
        "observedData",
        "tools",
    } <= enabled_node_scopes


def test_sync_scope_declares_reviewed_direct_relationship_scopes() -> None:
    payload = json.loads((ROOT / "mirror-sync" / "sync_scope.json").read_text(encoding="utf-8"))

    relationship_scopes = {
        str(scope["name"]): scope
        for scope in payload["relationship_scopes"]
        if isinstance(scope, dict)
    }

    observable_scope = relationship_scopes["indicator_extended_observable_based_on_direct_relationships"]
    threat_intel_scope = relationship_scopes["threat_intel_context_direct_relationships"]

    assert observable_scope["relationship_mode"] == "direct"
    assert observable_scope["enabled"] is True
    assert set(observable_scope["allowed_relationship_types"]) == {"based-on"}
    assert observable_scope["entity_type_node_scopes"] == {
        "Indicator": "indicator",
        "Domain-Name": "domain_name_observable",
        "Url": "url_observable",
        "File": "file_observable",
    }

    assert threat_intel_scope["relationship_mode"] == "direct"
    assert threat_intel_scope["enabled"] is True
    assert set(threat_intel_scope["allowed_relationship_types"]) == {
        "indicates",
        "uses",
        "targets",
        "related-to",
        "mitigates",
    }
    assert {
        "Indicator": "indicator",
        "Malware": "malware",
        "Vulnerability": "vulnerability",
        "Attack-Pattern": "attackPatterns",
        "Campaign": "campaigns",
        "Infrastructure": "infrastructures",
        "Intrusion-Set": "intrusionSets",
        "Report": "reports",
        "Grouping": "groupings",
        "Identity": "identities",
        "Sector": "sectors",
        "Course-Of-Action": "coursesOfAction",
        "Observed-Data": "observedData",
        "Tool": "tools",
    }.items() <= threat_intel_scope["entity_type_node_scopes"].items()


def test_indicator_scope_avoids_invalid_observable_value_field() -> None:
    payload = json.loads((ROOT / "mirror-sync" / "sync_scope.json").read_text(encoding="utf-8"))

    indicator_scope = next(
        scope
        for scope in payload["node_scopes"]
        if isinstance(scope, dict) and scope.get("name") == "indicator"
    )
    selection = str(indicator_scope["selection"])
    projection_properties = {
        str(property_mapping["property"])
        for property_mapping in indicator_scope["projection"]["properties"]
        if isinstance(property_mapping, dict) and property_mapping.get("property")
    }

    assert "observable_value" not in selection
    assert "observable_value" not in projection_properties
    assert "x_opencti_main_observable_type" in selection
    assert "pattern" in selection