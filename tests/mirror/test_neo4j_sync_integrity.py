from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from _fixture_support import load_env_file


ROOT = Path(__file__).resolve().parents[2]
PROTECTED_FIXTURE = Path(__file__).resolve().parent / "protected_fixtures" / "manual_seed_steps.md"
PROTECTED_BASELINE = Path(__file__).resolve().parent / "protected_baselines" / "cypher_assertions.md"


def _neo4j_http_endpoint(env_values: dict[str, str]) -> str:
    host = os.getenv("NEO4J_MIRROR_HTTP_HOST", env_values.get("NEO4J_ADVERTISED_HOST", "localhost"))
    port = os.getenv("NEO4J_MIRROR_HTTP_PORT", env_values.get("NEO4J_HTTP_PORT", "27474"))
    return f"http://{host}:{port}/db/neo4j/tx/commit"


def _neo4j_headers(env_values: dict[str, str]) -> dict[str, str]:
    username = os.getenv("NEO4J_MIRROR_USERNAME", "neo4j")
    password = os.getenv("NEO4J_MIRROR_PASSWORD", env_values.get("NEO4J_PASSWORD", ""))
    if not password:
        raise AssertionError("Missing Neo4j mirror password")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _run_cypher(env_values: dict[str, str], statement: str, parameters: dict[str, str]) -> list[dict[str, object]]:
    payload = json.dumps({
        "statements": [
            {
                "statement": statement,
                "parameters": parameters,
            }
        ]
    }).encode("utf-8")
    request = urllib.request.Request(
        _neo4j_http_endpoint(env_values),
        data=payload,
        headers=_neo4j_headers(env_values),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors", [])
    assert not errors, f"Neo4j query failed: {errors}"
    result = body["results"][0]
    columns = result.get("columns", [])
    rows = []
    for item in result.get("data", []):
        row = item.get("row", [])
        rows.append(dict(zip(columns, row, strict=False)))
    return rows


def _query_expected_rows(
    env_values: dict[str, str],
    *,
    expected_ipv4_value: str,
    expected_malware_name: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    node_rows = _run_cypher(
        env_values,
        (
            "MATCH (a:`ipv4-addr`) "
            "WHERE a.value = $ipv4_value "
            "RETURN a.value AS value, a.standard_id AS standard_id "
            "LIMIT 1"
        ),
        {"ipv4_value": expected_ipv4_value},
    )
    relationship_rows = _run_cypher(
        env_values,
        (
            "MATCH (a:`ipv4-addr`)-[r:indicates]->(b:malware) "
            "WHERE a.value = $ipv4_value AND b.name = $malware_name "
            "RETURN type(r) AS relation_type, b.name AS malware_name "
            "LIMIT 1"
        ),
        {"ipv4_value": expected_ipv4_value, "malware_name": expected_malware_name},
    )
    return node_rows, relationship_rows


def _wait_for_expected_rows(
    env_values: dict[str, str],
    *,
    expected_ipv4_value: str,
    expected_ipv4_standard_id: str,
    expected_malware_name: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    timeout_seconds = int(os.getenv("MIRROR_ASSERT_TIMEOUT_SECONDS", "90"))
    deadline = time.time() + timeout_seconds
    last_node_rows: list[dict[str, object]] = []
    last_relationship_rows: list[dict[str, object]] = []
    last_error: urllib.error.URLError | None = None

    while time.time() < deadline:
        try:
            node_rows, relationship_rows = _query_expected_rows(
                env_values,
                expected_ipv4_value=expected_ipv4_value,
                expected_malware_name=expected_malware_name,
            )
            last_node_rows = node_rows
            last_relationship_rows = relationship_rows
            last_error = None

            if (
                node_rows
                and node_rows[0]["standard_id"] == expected_ipv4_standard_id
                and relationship_rows
                and relationship_rows[0]["relation_type"] == "indicates"
                and relationship_rows[0]["malware_name"] == expected_malware_name
            ):
                return node_rows, relationship_rows
        except urllib.error.URLError as exc:
            last_error = exc

        time.sleep(3)

    if last_error is not None:
        pytest.fail(f"Neo4j mirror HTTP endpoint is unavailable: {last_error}")

    return last_node_rows, last_relationship_rows


def test_neo4j_sync_integrity(prepared_mirror_seed: dict[str, str]) -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen mirror acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen mirror acceptance entry"

    env_values = load_env_file()
    expected_ipv4_value = prepared_mirror_seed["ipv4_value"]
    expected_ipv4_standard_id = prepared_mirror_seed["ipv4_standard_id"]
    expected_malware_name = prepared_mirror_seed["malware_name"]

    node_rows, relationship_rows = _wait_for_expected_rows(
        env_values,
        expected_ipv4_value=expected_ipv4_value,
        expected_ipv4_standard_id=expected_ipv4_standard_id,
        expected_malware_name=expected_malware_name,
    )

    assert node_rows, "Mirror replica is missing the expected IPv4 node"
    assert node_rows[0]["standard_id"] == expected_ipv4_standard_id
    assert relationship_rows, "Mirror replica is missing the expected indicates relationship"
    assert relationship_rows[0]["relation_type"] == "indicates"
    assert relationship_rows[0]["malware_name"] == expected_malware_name