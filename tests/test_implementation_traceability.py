from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOT_CONTRACT = ROOT / "OVERALL_ARCHITECTURE.md"
MIRROR_SYNC_CONTRACT = ROOT / "mirror-sync" / "ARCHITECTURE.md"
QUERY_BACKEND_CONTRACT = ROOT / "query-backend" / "ARCHITECTURE.md"
QUERY_BACKEND_TEST_CONTRACT = ROOT / "tests" / "query_backend" / "ARCHITECTURE.md"


def test_root_contract_declares_replica_traceability_chain() -> None:
    text = ROOT_CONTRACT.read_text(encoding="utf-8")
    assert "OpenCTIToNeo4jMirrorSync" in text
    assert "mirror-sync/" in text
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
    backend_text = QUERY_BACKEND_CONTRACT.read_text(encoding="utf-8")
    test_text = QUERY_BACKEND_TEST_CONTRACT.read_text(encoding="utf-8")

    assert "直接 implements `OpenCTIToNeo4jMirrorSync`" in mirror_text
    assert "直接 implements `ReplicaGraphQueryBackend`" in backend_text
    assert "直接 implements `AIAgentGraphInvestigation`" in backend_text
    assert "Dockerfile" in backend_text
    assert "test_successful_query_returns_graph_payload_and_freshness_metadata" in test_text
    assert "直接 implements `受控 Cypher 拒绝与结构化反馈`" in test_text
    assert "直接 implements `副本降级不静默回退`" in test_text
    assert "直接 implements `Docker统一代理查询入口可用性验证`" in test_text