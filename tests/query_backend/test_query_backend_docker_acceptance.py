from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import pytest


PROTECTED_FIXTURE = Path(__file__).resolve().parent / "protected_fixtures" / "docker_proxy_probe.md"
PROTECTED_BASELINE = Path(__file__).resolve().parent / "protected_baselines" / "docker_proxy_contract.md"


def _docker_base_url() -> str:
    return os.getenv("QUERY_BACKEND_DOCKER_BASE_URL", "https://localhost").rstrip("/")


def _docker_request_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    auth_token = os.getenv("QUERY_BACKEND_AUTH_TOKEN", "").strip()
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def _post_via_proxy(payload: dict[str, object]) -> dict[str, object]:
    request_obj = urllib.request.Request(
        f"{_docker_base_url()}/graph/query",
        data=json.dumps(payload).encode("utf-8"),
        headers=_docker_request_headers(),
        method="POST",
    )
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request_obj, timeout=30, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if not body:
            raise AssertionError(f"Docker proxy entry rejected the request without a structured body: {exc}") from exc
        return json.loads(body)


def test_docker_proxy_entry_preserves_structured_rejection_contract() -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen docker query-backend acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen docker query-backend acceptance entry"

    payload = {
        "investigation_id": os.getenv("QUERY_BACKEND_INVESTIGATION_ID", "acceptance-docker-proxy"),
        "cypher": "CREATE (n:Blocked {name: 'docker-proxy-forbidden'}) RETURN n",
    }

    try:
        body = _post_via_proxy(payload)
    except urllib.error.URLError as exc:
        pytest.fail(f"Docker proxy query backend endpoint is unavailable: {exc}")

    assert body.get("backend") == "neo4j-replica"
    assert body.get("investigation_id") == payload["investigation_id"]
    assert body.get("rejection_reason"), "Docker proxy entry must preserve structured rejection_reason"
    assert body.get("budget_policy"), "Docker proxy entry must preserve structured budget_policy"
    assert body.get("fallback_backend") in (None, "neo4j-replica")