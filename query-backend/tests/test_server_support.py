from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "query-backend" / "server.py"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("query_backend_server", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_cypher_is_rejected_by_classifier() -> None:
    server = _load_server_module()
    assert server.is_readonly_cypher("MATCH (n) RETURN n LIMIT 1") is True
    assert server.is_readonly_cypher("CREATE (n:Blocked) RETURN n") is False


def test_degraded_response_keeps_replica_identity() -> None:
    server = _load_server_module()
    payload = {"investigation_id": "acceptance-degraded-replica"}
    freshness = {
        "backend": "neo4j-replica",
        "freshness_ts": "2026-05-13T07:52:00Z",
        "staleness_seconds": 960,
        "sync_status": "stale",
    }
    response = server.build_degraded(payload, freshness)
    assert response["backend"] == "neo4j-replica"
    assert response["sync_status"] == "stale"
    assert "freshness_ts" in response