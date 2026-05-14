from __future__ import annotations

import base64
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = ROOT / "mirror-sync" / "runtime"
TEST_BOOTSTRAP_ANCHOR_PATH = RUNTIME_DIR / "test_bootstrap_anchor.json"


def load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _opencti_graphql_endpoint(env_values: dict[str, str]) -> str:
    base_url = os.getenv("OPENCTI_BASE_URL", env_values.get("OPENCTI_BASE_URL", "https://localhost")).rstrip("/")
    return f"{base_url}/graphql"


def _opencti_graphql_headers(env_values: dict[str, str]) -> dict[str, str]:
    token = os.getenv("OPENCTI_ADMIN_TOKEN", env_values.get("OPENCTI_ADMIN_TOKEN", "")).strip()
    if not token:
        raise AssertionError("Missing OpenCTI admin token for mirror auto-seed flow")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _graphql_request(query: str, variables: dict[str, object]) -> dict[str, object]:
    env_values = load_env_file()
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    endpoint = _opencti_graphql_endpoint(env_values)
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers=_opencti_graphql_headers(env_values),
        method="POST",
    )
    ssl_context = ssl._create_unverified_context() if endpoint.startswith("https://") else None

    try:
        with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AssertionError(f"OpenCTI GraphQL request failed during mirror auto-seed: {exc}") from exc

    errors = body.get("errors")
    if errors:
        raise AssertionError(f"OpenCTI GraphQL returned errors during mirror auto-seed: {errors}")

    return body["data"]


def neo4j_http_endpoint(env_values: dict[str, str]) -> str:
    host = os.getenv("NEO4J_MIRROR_HTTP_HOST", env_values.get("NEO4J_ADVERTISED_HOST", "localhost"))
    port = os.getenv("NEO4J_MIRROR_HTTP_PORT", env_values.get("NEO4J_HTTP_PORT", "27474"))
    return f"http://{host}:{port}/db/neo4j/tx/commit"


def neo4j_headers(env_values: dict[str, str]) -> dict[str, str]:
    username = os.getenv("NEO4J_MIRROR_USERNAME", "neo4j")
    password = os.getenv("NEO4J_MIRROR_PASSWORD", env_values.get("NEO4J_PASSWORD", ""))
    if not password:
        raise AssertionError("Missing Neo4j mirror password")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def run_cypher(statement: str, parameters: dict[str, object]) -> list[dict[str, object]]:
    env_values = load_env_file()
    payload = json.dumps(
        {
            "statements": [
                {
                    "statement": statement,
                    "parameters": parameters,
                }
            ]
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        neo4j_http_endpoint(env_values),
        data=payload,
        headers=neo4j_headers(env_values),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors", [])
    if errors:
        raise AssertionError(f"Neo4j query failed: {errors}")
    result = body["results"][0]
    columns = result.get("columns", [])
    rows = []
    for item in result.get("data", []):
        row = item.get("row", [])
        rows.append(dict(zip(columns, row, strict=False)))
    return rows


def load_freshness() -> dict[str, object]:
    freshness_path = RUNTIME_DIR / "freshness.json"
    if not freshness_path.is_file():
        raise AssertionError(f"Missing replica freshness file: {freshness_path}")
    return json.loads(freshness_path.read_text(encoding="utf-8"))


def load_watermark_artifacts() -> list[Path]:
    return sorted(path for path in RUNTIME_DIR.glob("*watermark*") if path.is_file())


def _record_bootstrap_start_anchor() -> str:
    anchor = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    TEST_BOOTSTRAP_ANCHOR_PATH.write_text(
        json.dumps({"bootstrap_start_at": anchor}, indent=2),
        encoding="utf-8",
    )
    return anchor


def _wait_for_replica_projection(
    *,
    observable_standard_id: str,
    malware_standard_id: str,
) -> None:
    timeout_seconds = int(os.getenv("MIRROR_ASSERT_TIMEOUT_SECONDS", "90"))
    deadline = time.time() + timeout_seconds
    last_rows: list[dict[str, object]] = []
    last_freshness: dict[str, object] | None = None
    last_watermarks: list[str] = []
    last_error: AssertionError | urllib.error.URLError | None = None

    while time.time() < deadline:
        try:
            last_rows = run_cypher(
                (
                    "MATCH (observable:`ipv4-addr` {standard_id: $observable_standard_id}) "
                    "OPTIONAL MATCH (observable)-[r]->(malware:malware {standard_id: $malware_standard_id}) "
                    "RETURN observable.standard_id AS observable_standard_id, "
                    "       malware.standard_id AS malware_standard_id, "
                    "       type(r) AS relation_type "
                    "LIMIT 1"
                ),
                {
                    "observable_standard_id": observable_standard_id,
                    "malware_standard_id": malware_standard_id,
                },
            )
            last_freshness = load_freshness()
            last_watermarks = [str(path) for path in load_watermark_artifacts()]
            if (
                last_rows
                and last_rows[0]["observable_standard_id"] == observable_standard_id
                and last_rows[0]["malware_standard_id"] == malware_standard_id
                and last_rows[0]["relation_type"] == "indicates"
                and last_freshness.get("sync_status") == "healthy"
                and last_watermarks
            ):
                return
            last_error = None
        except (AssertionError, urllib.error.URLError) as exc:
            last_error = exc

        time.sleep(3)

    details = {
        "last_rows": last_rows,
        "last_freshness": last_freshness,
        "last_watermarks": last_watermarks,
        "anchor_path": str(TEST_BOOTSTRAP_ANCHOR_PATH),
    }
    if last_error is not None:
        raise AssertionError(
            "Timed out waiting for real mirror replica projection after GraphQL seeding: "
            f"{last_error}; context={details}"
        ) from last_error
    raise AssertionError(
        "Timed out waiting for real mirror replica projection after GraphQL seeding; "
        f"context={details}"
    )


def create_graphql_only_change(
    ipv4_value: str,
    malware_name: str,
    malware_description: str,
) -> dict[str, str]:
    observable = _graphql_request(
        (
            "mutation SeedMirrorIPv4($value: String!) {"
            " stixCyberObservableAdd(type: \"IPv4-Addr\", update: true, IPv4Addr: {value: $value}) {"
            "   id"
            "   standard_id"
            " }"
            "}"
        ),
        {"value": ipv4_value},
    )["stixCyberObservableAdd"]

    malware = _graphql_request(
        (
            "mutation SeedMirrorMalware($name: String!, $description: String!) {"
            " malwareAdd(input: {name: $name, description: $description}) {"
            "   id"
            "   standard_id"
            "   name"
            "   description"
            " }"
            "}"
        ),
        {"name": malware_name, "description": malware_description},
    )["malwareAdd"]

    indicator = _graphql_request(
        (
            "mutation SeedMirrorIndicator($name: String!, $pattern: String!) {"
            " indicatorAdd(input: {"
            "   name: $name,"
            "   pattern_type: \"stix\","
            "   pattern: $pattern,"
            "   x_opencti_main_observable_type: \"IPv4-Addr\","
            "   update: true"
            " }) {"
            "   id"
            "   standard_id"
            "   name"
            " }"
            "}"
        ),
        {
            "name": f"{malware_name} indicator for {ipv4_value}",
            "pattern": f"[ipv4-addr:value = '{ipv4_value}']",
        },
    )["indicatorAdd"]

    _graphql_request(
        (
            "mutation SeedMirrorBasedOn($fromId: StixRef!, $toId: StixRef!) {"
            " stixCoreRelationshipAdd(input: {fromId: $fromId, toId: $toId, relationship_type: \"based-on\"}) {"
            "   id"
            " }"
            "}"
        ),
        {"fromId": indicator["id"], "toId": observable["id"]},
    )["stixCoreRelationshipAdd"]

    relationship = _graphql_request(
        (
            "mutation SeedMirrorIndicates($fromId: StixRef!, $toId: StixRef!) {"
            " stixCoreRelationshipAdd(input: {fromId: $fromId, toId: $toId, relationship_type: \"indicates\"}) {"
            "   id"
            "   relationship_type"
            " }"
            "}"
        ),
        {"fromId": indicator["id"], "toId": malware["id"]},
    )["stixCoreRelationshipAdd"]

    return {
        "ipv4_value": ipv4_value,
        "ipv4_standard_id": observable["standard_id"],
        "malware_name": malware["name"],
        "malware_description": malware["description"],
        "malware_standard_id": malware["standard_id"],
        "indicator_standard_id": indicator["standard_id"],
        "relationship_id": relationship["id"],
    }


def ensure_mirror_seed_fixture(ipv4_value: str, malware_name: str) -> dict[str, str]:
    bootstrap_start_at = _record_bootstrap_start_anchor()
    malware_description = f"{malware_name} description for replica projection checks"

    observable = _graphql_request(
        (
            "mutation SeedMirrorIPv4($value: String!) {"
            " stixCyberObservableAdd(type: \"IPv4-Addr\", update: true, IPv4Addr: {value: $value}) {"
            "   id"
            "   standard_id"
            " }"
            "}"
        ),
        {"value": ipv4_value},
    )["stixCyberObservableAdd"]

    malware = _graphql_request(
        (
            "mutation SeedMirrorMalware($name: String!, $description: String!) {"
            " malwareAdd(input: {name: $name, description: $description}) {"
            "   id"
            "   standard_id"
            "   name"
            "   description"
            " }"
            "}"
        ),
        {"name": malware_name, "description": malware_description},
    )["malwareAdd"]

    indicator = _graphql_request(
        (
            "mutation SeedMirrorIndicator($name: String!, $pattern: String!) {"
            " indicatorAdd(input: {"
            "   name: $name,"
            "   pattern_type: \"stix\","
            "   pattern: $pattern,"
            "   x_opencti_main_observable_type: \"IPv4-Addr\","
            "   update: true"
            " }) {"
            "   id"
            "   standard_id"
            "   name"
            " }"
            "}"
        ),
        {
            "name": f"{malware_name} indicator for {ipv4_value}",
            "pattern": f"[ipv4-addr:value = '{ipv4_value}']",
        },
    )["indicatorAdd"]

    _graphql_request(
        (
            "mutation SeedMirrorBasedOn($fromId: StixRef!, $toId: StixRef!) {"
            " stixCoreRelationshipAdd(input: {fromId: $fromId, toId: $toId, relationship_type: \"based-on\"}) {"
            "   id"
            " }"
            "}"
        ),
        {"fromId": indicator["id"], "toId": observable["id"]},
    )["stixCoreRelationshipAdd"]

    relationship = _graphql_request(
        (
            "mutation SeedMirrorIndicates($fromId: StixRef!, $toId: StixRef!) {"
            " stixCoreRelationshipAdd(input: {fromId: $fromId, toId: $toId, relationship_type: \"indicates\"}) {"
            "   id"
            "   relationship_type"
            " }"
            "}"
        ),
        {"fromId": indicator["id"], "toId": malware["id"]},
    )["stixCoreRelationshipAdd"]

    _wait_for_replica_projection(
        observable_standard_id=observable["standard_id"],
        malware_standard_id=malware["standard_id"],
    )

    return {
        "bootstrap_start_at": bootstrap_start_at,
        "ipv4_value": ipv4_value,
        "ipv4_standard_id": observable["standard_id"],
        "malware_name": malware["name"],
        "malware_description": malware["description"],
        "malware_standard_id": malware["standard_id"],
        "observable_id": observable["id"],
        "indicator_id": indicator["id"],
        "indicator_standard_id": indicator["standard_id"],
        "malware_id": malware["id"],
        "relationship_id": relationship["id"],
        "relationship_type": relationship["relationship_type"],
    }