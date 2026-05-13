from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


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


def ensure_mirror_seed_fixture(ipv4_value: str, malware_name: str) -> dict[str, str]:
    observable = _graphql_request(
        (
            "mutation SeedMirrorIPv4($value: String!) {"
            " stixCyberObservableAdd(input: {type: \"IPv4-Addr\", observable_value: $value}) {"
            "   id"
            "   standard_id"
            " }"
            "}"
        ),
        {"value": ipv4_value},
    )["stixCyberObservableAdd"]

    malware = _graphql_request(
        (
            "mutation SeedMirrorMalware($name: String!) {"
            " malwareAdd(input: {name: $name}) {"
            "   id"
            "   standard_id"
            "   name"
            " }"
            "}"
        ),
        {"name": malware_name},
    )["malwareAdd"]

    relationship = _graphql_request(
        (
            "mutation SeedMirrorRelationship($fromId: String!, $toId: String!) {"
            " stixCoreRelationshipAdd(input: {fromId: $fromId, toId: $toId, relationship_type: \"indicates\"}) {"
            "   id"
            "   relationship_type"
            " }"
            "}"
        ),
        {"fromId": observable["id"], "toId": malware["id"]},
    )["stixCoreRelationshipAdd"]

    return {
        "ipv4_value": ipv4_value,
        "ipv4_standard_id": observable["standard_id"],
        "malware_name": malware["name"],
        "observable_id": observable["id"],
        "malware_id": malware["id"],
        "relationship_id": relationship["id"],
        "relationship_type": relationship["relationship_type"],
    }