from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
PROTECTED_FIXTURE = Path(__file__).resolve().parent / "protected_fixtures" / "rejected_cypher_and_degraded_probe.md"
PROTECTED_BASELINE = Path(__file__).resolve().parent / "protected_baselines" / "response_contract.md"


def _required_base_url(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default or "").strip()
    if not value:
        raise AssertionError(f"Missing required query-backend test environment variable: {name}")
    return value.rstrip("/")


def _backend_endpoint(*, degraded: bool = False) -> str:
    if degraded:
        base_url = _required_base_url("QUERY_BACKEND_DEGRADED_BASE_URL")
    else:
        base_url = _required_base_url("QUERY_BACKEND_BASE_URL", "http://localhost:8088")
    return f"{base_url}/graph/query"


def _request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    auth_token = os.getenv("QUERY_BACKEND_AUTH_TOKEN", "").strip()
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def _post_query(payload: dict[str, object], *, degraded: bool = False) -> dict[str, object]:
    request = urllib.request.Request(
        _backend_endpoint(degraded=degraded),
        data=json.dumps(payload).encode("utf-8"),
        headers=_request_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if not body:
            raise AssertionError(f"Query backend rejected the request without a structured body: {exc}") from exc
        return json.loads(body)


def test_successful_query_returns_graph_payload_and_freshness_metadata() -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen query-backend acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen query-backend acceptance entry"

    payload = {
        "investigation_id": os.getenv("QUERY_BACKEND_INVESTIGATION_ID", "acceptance-success-path"),
        "cypher": os.getenv("QUERY_BACKEND_SUCCESS_CYPHER", "MATCH (n) RETURN n LIMIT 1"),
    }

    try:
        body = _post_query(payload)
    except urllib.error.URLError as exc:
        pytest.fail(f"Query backend endpoint is unavailable: {exc}")

    assert body.get("backend") == "neo4j-replica"
    assert body.get("investigation_id") == payload["investigation_id"]
    assert body.get("freshness_ts"), "Successful query must surface freshness_ts"
    assert "staleness_seconds" in body, "Successful query must surface staleness_seconds"
    assert body.get("sync_status"), "Successful query must surface sync_status"
    assert not body.get("rejection_reason"), "Successful query must not be reported as a rejection"

    results = body.get("results")
    assert isinstance(results, list), "Successful query must return a results list for machine consumption"
    assert not body.get("result_truncated") or isinstance(body.get("result_truncated"), bool)


def test_controlled_cypher_rejection_returns_structured_feedback() -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen query-backend acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen query-backend acceptance entry"

    payload = {
        "investigation_id": os.getenv("QUERY_BACKEND_INVESTIGATION_ID", "acceptance-controlled-rejection"),
        "cypher": "CREATE (n:Blocked {name: 'forbidden'}) RETURN n",
    }

    try:
        body = _post_query(payload)
    except urllib.error.URLError as exc:
        pytest.fail(f"Query backend endpoint is unavailable: {exc}")

    assert body.get("rejection_reason"), "Controlled Cypher rejection must return a structured rejection_reason"
    assert body.get("budget_policy"), "Controlled Cypher rejection must return the applied budget_policy"
    assert body.get("investigation_id") == payload["investigation_id"]


def test_replica_degradation_does_not_fall_back_silently() -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen query-backend acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen query-backend acceptance entry"

    payload = {
        "investigation_id": os.getenv("QUERY_BACKEND_INVESTIGATION_ID", "acceptance-degraded-replica"),
        "cypher": "MATCH p=(a)-[*1..2]->(b) RETURN p LIMIT 5",
    }

    try:
        body = _post_query(payload, degraded=True)
    except urllib.error.URLError as exc:
        pytest.fail(f"Query backend endpoint is unavailable: {exc}")

    assert body.get("backend") == "neo4j-replica"
    assert body.get("freshness_ts"), "Degraded response must surface freshness_ts"
    assert "staleness_seconds" in body, "Degraded response must surface staleness_seconds"
    assert body.get("sync_status"), "Degraded response must surface sync_status"
    assert body.get("fallback_backend") in (None, "neo4j-replica"), "Degraded response must not silently fall back to GraphQL"