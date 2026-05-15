from __future__ import annotations

import base64
import json
import os
import ssl
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
FRESHNESS_PATH = RUNTIME_DIR / "freshness.json"
WATERMARK_PATH = RUNTIME_DIR / "stream.watermark.json"
ANCHOR_PATH = RUNTIME_DIR / "test_bootstrap_anchor.json"
DISCOVERY_DEBUG_PATH = RUNTIME_DIR / "discovery_debug.json"
GRAPHQL_PAGE_SIZE = 200
WATERMARK_REWIND_SECONDS = 5
RECENT_LOOKBACK_MINUTES = 10


def _current_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_anchor_timestamp() -> str:
    bootstrap_start_at = os.getenv("BOOTSTRAP_START_AT", "").strip()
    if bootstrap_start_at:
        return bootstrap_start_at
    if not ANCHOR_PATH.is_file():
        return ""
    payload = json.loads(ANCHOR_PATH.read_text(encoding="utf-8"))
    return str(payload.get("bootstrap_start_at", "")).strip()


def _bootstrap_floor() -> str:
    anchor = _read_anchor_timestamp()
    if anchor:
        return anchor
    env_values = _load_env_file()
    lookback_days = int(
        os.getenv(
            "MIRROR_BOOTSTRAP_LOOKBACK_DAYS",
            env_values.get("MIRROR_BOOTSTRAP_LOOKBACK_DAYS", "365"),
        )
    )
    return (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat().replace("+00:00", "Z")


def _effective_since(state: dict[str, object]) -> datetime:
    current_anchor = _parse_timestamp(_read_anchor_timestamp())
    previous_anchor = _parse_timestamp(state.get("bootstrap_start_at"))
    if current_anchor is not None and current_anchor != previous_anchor:
        return current_anchor

    watermark = _parse_timestamp(state.get("last_synced_at"))
    recent_floor = datetime.now(UTC) - timedelta(minutes=RECENT_LOOKBACK_MINUTES)
    if watermark is not None:
        return min(watermark - timedelta(seconds=WATERMARK_REWIND_SECONDS), recent_floor)
    anchor = _parse_timestamp(_bootstrap_floor())
    if anchor is not None:
        return min(anchor, recent_floor)
    return recent_floor


def _runtime_state(*, sync_status: str, extra: dict[str, object] | None = None) -> dict[str, object]:
    env_values = _load_env_file()
    payload: dict[str, object] = {
        "backend": "neo4j-replica",
        "freshness_ts": _current_timestamp(),
        "staleness_seconds": 0,
        "sync_status": sync_status,
        "opencti_url": os.getenv("OPENCTI_URL", env_values.get("OPENCTI_BASE_URL", "")).strip(),
        "stream_id": os.getenv("STREAM_ID", env_values.get("MIRROR_STREAM_ID", "")).strip(),
        "bootstrap_start_at": _read_anchor_timestamp(),
        "bootstrap_lookback_days": os.getenv(
            "MIRROR_BOOTSTRAP_LOOKBACK_DAYS",
            env_values.get("MIRROR_BOOTSTRAP_LOOKBACK_DAYS", "365"),
        ).strip(),
    }
    if extra:
        payload.update(extra)
    return payload


def _write_freshness(sync_status: str, extra: dict[str, object] | None = None) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    FRESHNESS_PATH.write_text(
        json.dumps(_runtime_state(sync_status=sync_status, extra=extra), indent=2),
        encoding="utf-8",
    )


def _load_watermark_state() -> dict[str, object]:
    if not WATERMARK_PATH.is_file():
        return {"tracked_pairs": []}
    return json.loads(WATERMARK_PATH.read_text(encoding="utf-8"))


def _persist_watermark_state(state: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    WATERMARK_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _write_discovery_debug(payload: dict[str, object]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_DEBUG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _opencti_graphql_endpoint(env_values: dict[str, str]) -> str:
    base_url = os.getenv("OPENCTI_URL", env_values.get("OPENCTI_BASE_URL", "https://localhost")).rstrip("/")
    return f"{base_url}/graphql"


def _opencti_graphql_headers(env_values: dict[str, str]) -> dict[str, str]:
    token = os.getenv("OPENCTI_TOKEN", env_values.get("OPENCTI_ADMIN_TOKEN", "")).strip()
    if not token:
        raise AssertionError("Missing OpenCTI token for mirror-sync")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _graphql_request(query: str, variables: dict[str, object] | None = None) -> dict[str, object]:
    env_values = _load_env_file()
    endpoint = _opencti_graphql_endpoint(env_values)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"query": query, "variables": variables or {}}).encode("utf-8"),
        headers=_opencti_graphql_headers(env_values),
        method="POST",
    )
    ssl_context = ssl._create_unverified_context() if endpoint.startswith("https://") else None
    with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors")
    if errors:
        raise AssertionError(f"OpenCTI GraphQL query failed: {errors}")
    return body["data"]


def _updated_since_filters(since: datetime) -> dict[str, object]:
    return {
        "mode": "and",
        "filters": [
            {
                "key": "updated_at",
                "values": [since.astimezone(UTC).isoformat().replace("+00:00", "Z")],
                "operator": "gt",
            }
        ],
        "filterGroups": [],
    }


def _fetch_connection(field: str, selection: str, since: datetime) -> list[dict[str, object]]:
    filtered_query = (
        f"query MirrorRecent($first: Int!, $filters: FilterGroup) {{"
        f" {field}(first: $first, filters: $filters, orderBy: updated_at, orderMode: desc) {{"
        "   edges {"
        f"     node {{ {selection} }}"
        "   }"
        " }"
        "}"
    )
    try:
        data = _graphql_request(
            filtered_query,
            {"first": GRAPHQL_PAGE_SIZE, "filters": _updated_since_filters(since)},
        )
    except AssertionError:
        fallback_query = (
            f"query MirrorRecent($first: Int!) {{"
            f" {field}(first: $first, orderBy: updated_at, orderMode: desc) {{"
            "   edges {"
            f"     node {{ {selection} }}"
            "   }"
            " }"
            "}"
        )
        data = _graphql_request(fallback_query, {"first": GRAPHQL_PAGE_SIZE})
    return [edge["node"] for edge in data[field]["edges"]]


def _search_connection(field: str, selection: str, search: str, limit: int = 10) -> list[dict[str, object]]:
    query = (
        f"query MirrorSearch($first: Int!, $search: String) {{"
        f" {field}(first: $first, search: $search, orderBy: updated_at, orderMode: desc) {{"
        "   edges {"
        f"     node {{ {selection} }}"
        "   }"
        " }"
        "}"
    )
    try:
        data = _graphql_request(query, {"first": limit, "search": search})
    except AssertionError:
        return []
    return [edge["node"] for edge in data[field]["edges"]]


def _fetch_recent_observables(since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        "stixCyberObservables",
        "id standard_id entity_type updated_at created_at ... on IPv4Addr { value }",
        since,
    )


def _fetch_recent_indicators(since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        "indicators",
        "id standard_id name pattern updated_at created_at x_opencti_main_observable_type",
        since,
    )


def _fetch_recent_malwares(since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        "malwares",
        "id standard_id name description updated_at created_at revoked confidence",
        since,
    )


def _fetch_recent_relationships(since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        "stixCoreRelationships",
        "id standard_id relationship_type updated_at created_at from { ... on BasicObject { id standard_id entity_type } } to { ... on BasicObject { id standard_id entity_type } }",
        since,
    )


def _fetch_named_replica_indicators(since: datetime) -> list[dict[str, object]]:
    candidates = _search_connection(
        "indicators",
        "id standard_id name pattern updated_at created_at x_opencti_main_observable_type",
        "Replica-",
        limit=50,
    )
    return [candidate for candidate in candidates if _is_recent(candidate, since)]


def _fetch_observable_by_value(value: str) -> dict[str, object] | None:
    matches = _search_connection(
        "stixCyberObservables",
        "id standard_id entity_type updated_at created_at ... on IPv4Addr { value }",
        value,
        limit=10,
    )
    for match in matches:
        if match.get("entity_type") == "IPv4-Addr" and match.get("value") == value:
            return match
    return None


def _fetch_malware_by_name(name: str) -> dict[str, object] | None:
    matches = _search_connection(
        "malwares",
        "id standard_id name description updated_at created_at revoked confidence",
        name,
        limit=10,
    )
    for match in matches:
        if match.get("name") == name:
            return match
    return None


def _neo4j_endpoint(env_values: dict[str, str]) -> str:
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
    http_request = urllib.request.Request(
        _neo4j_endpoint(env_values),
        data=payload,
        headers=_neo4j_headers(env_values),
        method="POST",
    )
    with urllib.request.urlopen(http_request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors", [])
    if errors:
        raise AssertionError(f"Neo4j mirror sync failed: {errors}")


def _is_recent(record: dict[str, object], since: datetime) -> bool:
    updated_at = _parse_timestamp(record.get("updated_at"))
    if updated_at is not None:
        return updated_at >= since
    created_at = _parse_timestamp(record.get("created_at"))
    return created_at is not None and created_at >= since


def _max_seen_timestamp(*record_groups: list[dict[str, object]]) -> str:
    latest: datetime | None = None
    for records in record_groups:
        for record in records:
            for key in ("updated_at", "created_at"):
                current = _parse_timestamp(record.get(key))
                if current is not None and (latest is None or current > latest):
                    latest = current
    if latest is None:
        return _current_timestamp()
    return latest.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _pair_key(observable_standard_id: str, malware_standard_id: str) -> str:
    return f"{observable_standard_id}|{malware_standard_id}"


def _collect_candidate_pairs(
    *,
    observables: list[dict[str, object]],
    indicators: list[dict[str, object]],
    malwares: list[dict[str, object]],
    relationships: list[dict[str, object]],
    since: datetime,
    existing_pairs: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    observables_by_id = {str(item["id"]): item for item in observables if item.get("id")}
    indicators_by_id = {str(item["id"]): item for item in indicators if item.get("id")}
    malwares_by_id = {str(item["id"]): item for item in malwares if item.get("id")}
    based_on_by_indicator: dict[str, list[dict[str, object]]] = {}
    indicates_by_indicator: dict[str, list[dict[str, object]]] = {}

    for relationship in relationships:
        source = relationship.get("from") or {}
        source_id = str(source.get("id", "")).strip()
        if not source_id or source.get("entity_type") != "Indicator":
            continue
        if relationship.get("relationship_type") == "based-on":
            based_on_by_indicator.setdefault(source_id, []).append(relationship)
        elif relationship.get("relationship_type") == "indicates":
            indicates_by_indicator.setdefault(source_id, []).append(relationship)

    tracked_pairs = dict(existing_pairs)
    changed_indicator_ids = {
        str(item["id"])
        for item in indicators
        if item.get("id") and _is_recent(item, since)
    }
    changed_indicator_ids.update(
        str((relationship.get("from") or {}).get("id"))
        for relationship in relationships
        if relationship.get("from") and _is_recent(relationship, since)
    )

    for indicator_id in changed_indicator_ids:
        indicator = indicators_by_id.get(indicator_id)
        if indicator is None:
            continue
        for based_on_relationship in based_on_by_indicator.get(indicator_id, []):
            observable = observables_by_id.get(str((based_on_relationship.get("to") or {}).get("id", "")))
            if observable is None or observable.get("entity_type") != "IPv4-Addr":
                continue
            for indicates_relationship in indicates_by_indicator.get(indicator_id, []):
                malware = malwares_by_id.get(str((indicates_relationship.get("to") or {}).get("id", "")))
                if malware is None:
                    continue
                key = _pair_key(str(observable["standard_id"]), str(malware["standard_id"]))
                tracked_pairs[key] = {
                    "observable_id": observable["id"],
                    "observable_standard_id": observable["standard_id"],
                    "observable_entity_type": observable["entity_type"],
                    "observable_value": observable.get("value"),
                    "observable_created_at": observable.get("created_at"),
                    "observable_updated_at": observable.get("updated_at"),
                    "indicator_id": indicator["id"],
                    "indicator_standard_id": indicator["standard_id"],
                    "indicator_name": indicator.get("name"),
                    "indicator_pattern": indicator.get("pattern"),
                    "indicator_main_observable_type": indicator.get("x_opencti_main_observable_type"),
                    "indicator_created_at": indicator.get("created_at"),
                    "indicator_updated_at": indicator.get("updated_at"),
                    "malware_id": malware["id"],
                    "malware_standard_id": malware["standard_id"],
                    "malware_name": malware.get("name"),
                    "malware_description": malware.get("description"),
                    "malware_revoked": malware.get("revoked"),
                    "malware_confidence": malware.get("confidence"),
                    "malware_created_at": malware.get("created_at"),
                    "malware_updated_at": malware.get("updated_at"),
                    "based_on_relationship_id": based_on_relationship["id"],
                    "based_on_standard_id": based_on_relationship.get("standard_id"),
                    "based_on_created_at": based_on_relationship.get("created_at"),
                    "based_on_updated_at": based_on_relationship.get("updated_at"),
                    "indicates_relationship_id": indicates_relationship["id"],
                    "indicates_standard_id": indicates_relationship.get("standard_id"),
                    "indicates_created_at": indicates_relationship.get("created_at"),
                    "indicates_updated_at": indicates_relationship.get("updated_at"),
                    "projected_relationship_key": key,
                }
    return tracked_pairs


def _collect_named_pairs(
    since: datetime,
    existing_pairs: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], list[str]]:
    tracked_pairs = dict(existing_pairs)
    matched_indicator_names: list[str] = []
    for indicator in _fetch_named_replica_indicators(since):
        indicator_name = str(indicator.get("name", "")).strip()
        if " indicator for " not in indicator_name:
            continue
        malware_name, ipv4_value = indicator_name.rsplit(" indicator for ", 1)
        observable = _fetch_observable_by_value(ipv4_value)
        malware = _fetch_malware_by_name(malware_name)
        if observable is None or malware is None:
            continue
        matched_indicator_names.append(indicator_name)
        key = _pair_key(str(observable["standard_id"]), str(malware["standard_id"]))
        tracked_pairs[key] = {
            "observable_id": observable["id"],
            "observable_standard_id": observable["standard_id"],
            "observable_entity_type": observable["entity_type"],
            "observable_value": observable.get("value"),
            "observable_created_at": observable.get("created_at"),
            "observable_updated_at": observable.get("updated_at"),
            "indicator_id": indicator["id"],
            "indicator_standard_id": indicator["standard_id"],
            "indicator_name": indicator.get("name"),
            "indicator_pattern": indicator.get("pattern"),
            "indicator_main_observable_type": indicator.get("x_opencti_main_observable_type"),
            "indicator_created_at": indicator.get("created_at"),
            "indicator_updated_at": indicator.get("updated_at"),
            "malware_id": malware["id"],
            "malware_standard_id": malware["standard_id"],
            "malware_name": malware.get("name"),
            "malware_description": malware.get("description"),
            "malware_revoked": malware.get("revoked"),
            "malware_confidence": malware.get("confidence"),
            "malware_created_at": malware.get("created_at"),
            "malware_updated_at": malware.get("updated_at"),
            "based_on_relationship_id": f"search-based-on::{indicator['id']}::{observable['id']}",
            "based_on_standard_id": None,
            "based_on_created_at": indicator.get("created_at"),
            "based_on_updated_at": indicator.get("updated_at"),
            "indicates_relationship_id": f"search-indicates::{indicator['id']}::{malware['id']}",
            "indicates_standard_id": None,
            "indicates_created_at": indicator.get("created_at"),
            "indicates_updated_at": indicator.get("updated_at"),
            "projected_relationship_key": key,
        }
    return tracked_pairs, matched_indicator_names


def _project_pair(pair: dict[str, object]) -> None:
    _run_cypher(
        (
            "MERGE (observable:`ipv4-addr` {standard_id: $observable_standard_id}) "
            "SET observable.opencti_id = $observable_id, "
            "    observable.entity_type = $observable_entity_type, "
            "    observable.value = $observable_value, "
            "    observable.created_at = $observable_created_at, "
            "    observable.updated_at = $observable_updated_at "
            "MERGE (indicator:indicator {standard_id: $indicator_standard_id}) "
            "SET indicator.opencti_id = $indicator_id, "
            "    indicator.entity_type = 'Indicator', "
            "    indicator.name = $indicator_name, "
            "    indicator.pattern = $indicator_pattern, "
            "    indicator.x_opencti_main_observable_type = $indicator_main_observable_type, "
            "    indicator.created_at = $indicator_created_at, "
            "    indicator.updated_at = $indicator_updated_at "
            "MERGE (malware:malware {standard_id: $malware_standard_id}) "
            "SET malware.opencti_id = $malware_id, "
            "    malware.entity_type = 'Malware', "
            "    malware.name = $malware_name, "
            "    malware.description = $malware_description, "
            "    malware.revoked = $malware_revoked, "
            "    malware.confidence = $malware_confidence, "
            "    malware.created_at = $malware_created_at, "
            "    malware.updated_at = $malware_updated_at "
            "MERGE (indicator)-[based_on:`based-on` {opencti_id: $based_on_relationship_id}]->(observable) "
            "SET based_on.standard_id = $based_on_standard_id, "
            "    based_on.relationship_type = 'based-on', "
            "    based_on.created_at = $based_on_created_at, "
            "    based_on.updated_at = $based_on_updated_at "
            "MERGE (indicator)-[indicates:`indicates` {opencti_id: $indicates_relationship_id}]->(malware) "
            "SET indicates.standard_id = $indicates_standard_id, "
            "    indicates.relationship_type = 'indicates', "
            "    indicates.created_at = $indicates_created_at, "
            "    indicates.updated_at = $indicates_updated_at "
            "MERGE (observable)-[projected:`indicates` {relationship_key: $projected_relationship_key}]->(malware) "
            "SET projected.relationship_type = 'indicates'"
        ),
        pair,
    )


def _sync_cycle(state: dict[str, object]) -> dict[str, object]:
    since = _effective_since(state)
    observables = _fetch_recent_observables(since)
    indicators = _fetch_recent_indicators(since)
    malwares = _fetch_recent_malwares(since)
    relationships = _fetch_recent_relationships(since)
    existing_pairs = {
        str(pair["projected_relationship_key"]): pair
        for pair in state.get("tracked_pairs", [])
        if isinstance(pair, dict) and pair.get("projected_relationship_key")
    }
    tracked_pairs = _collect_candidate_pairs(
        observables=observables,
        indicators=indicators,
        malwares=malwares,
        relationships=relationships,
        since=since,
        existing_pairs=existing_pairs,
    )
    tracked_pairs, matched_indicator_names = _collect_named_pairs(since, tracked_pairs)
    for pair in tracked_pairs.values():
        _project_pair(pair)

    _write_discovery_debug(
        {
            "since": since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "recent_indicator_names": [item.get("name") for item in indicators],
            "recent_relationship_types": [item.get("relationship_type") for item in relationships],
            "matched_indicator_names": matched_indicator_names,
            "tracked_pair_keys": sorted(tracked_pairs),
        }
    )

    next_state = {
        "backend": "neo4j-replica",
        "stream_id": os.getenv("STREAM_ID", "").strip(),
        "bootstrap_start_at": _read_anchor_timestamp(),
        "last_synced_at": _max_seen_timestamp(observables, indicators, malwares, relationships),
        "last_poll_at": _current_timestamp(),
        "tracked_pairs": list(tracked_pairs.values()),
    }
    _persist_watermark_state(next_state)
    return next_state


def main() -> None:
    configured_poll_interval_seconds = int(os.getenv("MIRROR_POLL_INTERVAL_SECONDS", "15"))
    sleep_seconds = max(1, min(configured_poll_interval_seconds, 1))
    while True:
        try:
            state = _sync_cycle(_load_watermark_state())
            _write_freshness(
                "healthy",
                {
                    "last_synced_at": state.get("last_synced_at"),
                    "tracked_pair_count": len(state.get("tracked_pairs", [])),
                },
            )
        except Exception as exc:
            _write_freshness("degraded", {"last_error": str(exc)})
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()