from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
FRESHNESS_PATH = RUNTIME_DIR / "freshness.json"


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _neo4j_endpoint(env_values: dict[str, str]) -> str:
    host = os.getenv("NEO4J_MIRROR_HTTP_HOST", env_values.get("NEO4J_ADVERTISED_HOST", "localhost"))
    port = os.getenv("NEO4J_MIRROR_HTTP_PORT", env_values.get("NEO4J_HTTP_PORT", "7474"))
    return f"http://{host}:{port}/db/neo4j/tx/commit"


def _neo4j_headers(env_values: dict[str, str]) -> dict[str, str]:
    import base64

    username = os.getenv("NEO4J_MIRROR_USERNAME", "neo4j")
    password = os.getenv("NEO4J_MIRROR_PASSWORD", env_values.get("NEO4J_PASSWORD", ""))
    if not password:
        raise AssertionError("Missing Neo4j mirror password")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _run_cypher(statement: str, parameters: dict[str, object]) -> None:
    env_values = _load_env_file()
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
    http_request = request.Request(
        _neo4j_endpoint(env_values),
        data=payload,
        headers=_neo4j_headers(env_values),
        method="POST",
    )
    with request.urlopen(http_request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors", [])
    if errors:
        raise AssertionError(f"Neo4j mirror sync failed: {errors}")


def _write_freshness(sync_status: str) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    freshness = {
        "backend": "neo4j-replica",
        "freshness_ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "staleness_seconds": 0,
        "sync_status": sync_status,
    }
    FRESHNESS_PATH.write_text(json.dumps(freshness, indent=2), encoding="utf-8")


def sync_hot_subgraph(seed: dict[str, str]) -> None:
    _run_cypher(
        (
            "MERGE (observable:`ipv4-addr` {standard_id: $observable_standard_id}) "
            "SET observable.value = $ipv4_value, "
            "    observable.opencti_id = $observable_id "
            "MERGE (indicator:indicator {standard_id: $indicator_standard_id}) "
            "SET indicator.opencti_id = $indicator_id "
            "MERGE (malware:malware {standard_id: $malware_standard_id}) "
            "SET malware.name = $malware_name, "
            "    malware.opencti_id = $malware_id "
            "MERGE (observable)-[projected:indicates {opencti_projection_id: $relationship_id}]->(malware) "
            "SET projected.relationship_type = $relationship_type, "
            "    projected.projected_via = 'indicator-based-on'"
        ),
        seed,
    )
    _write_freshness("healthy")


if __name__ == "__main__":
    raise SystemExit("sync_once.py is a library entrypoint; import sync_hot_subgraph() instead.")