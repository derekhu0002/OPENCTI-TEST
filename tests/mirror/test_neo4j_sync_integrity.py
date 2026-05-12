from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
PROTECTED_FIXTURE = Path(__file__).resolve().parent / "protected_fixtures" / "manual_seed_steps.md"
PROTECTED_BASELINE = Path(__file__).resolve().parent / "protected_baselines" / "cypher_assertions.md"


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _require_opt_in() -> None:
    if os.getenv("OPENCTI_MIRROR_VALIDATE", "0") != "1":
        pytest.skip("Mirror runtime validation is opt-in. Set OPENCTI_MIRROR_VALIDATE=1 to run the frozen acceptance entry.")


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


def test_neo4j_sync_integrity() -> None:
    assert PROTECTED_FIXTURE.is_file(), "Protected fixture file is required for the frozen mirror acceptance entry"
    assert PROTECTED_BASELINE.is_file(), "Protected baseline file is required for the frozen mirror acceptance entry"

    _require_opt_in()
    env_values = _load_env_file()
    expected_ipv4_value = os.getenv("MIRROR_EXPECTED_IPV4_VALUE", "1.2.3.4")
    expected_ipv4_standard_id = os.getenv("MIRROR_EXPECTED_IPV4_STANDARD_ID", "").strip()
    expected_malware_name = os.getenv("MIRROR_EXPECTED_MALWARE_NAME", "Mirai-Botnet")

    if not expected_ipv4_standard_id:
        pytest.skip("Set MIRROR_EXPECTED_IPV4_STANDARD_ID to validate standard_id parity against the mirror replica.")

    try:
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
    except urllib.error.URLError as exc:
        pytest.fail(f"Neo4j mirror HTTP endpoint is unavailable: {exc}")

    assert node_rows, "Mirror replica is missing the expected IPv4 node"
    assert node_rows[0]["standard_id"] == expected_ipv4_standard_id
    assert relationship_rows, "Mirror replica is missing the expected indicates relationship"
    assert relationship_rows[0]["relation_type"] == "indicates"
    assert relationship_rows[0]["malware_name"] == expected_malware_name