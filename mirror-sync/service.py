from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import ssl
import time
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
RUNTIME_DIR = Path(__file__).resolve().parent / "runtime"
SYNC_SCOPE_PATH = Path(__file__).resolve().parent / "sync_scope.json"
FULL_SCOPE_CATALOG_PATH = Path(__file__).resolve().parent / "sync_scope.full.json"
FRESHNESS_PATH = RUNTIME_DIR / "freshness.json"
WATERMARK_PATH = RUNTIME_DIR / "stream.watermark.json"
ANCHOR_PATH = RUNTIME_DIR / "test_bootstrap_anchor.json"
DISCOVERY_DEBUG_PATH = RUNTIME_DIR / "discovery_debug.json"
GRAPHQL_PAGE_SIZE = 200
WATERMARK_REWIND_SECONDS = 5
RECENT_LOOKBACK_MINUTES = 10
IPV4_PATTERN_RE = re.compile(r"\[ipv4-addr:value = '([^']+)'\]")
REQUIRED_NODE_SCOPE_NAMES = {"ipv4_observable", "indicator", "malware", "vulnerability"}
REQUIRED_RELATIONSHIP_SCOPE_NAMES = {"indicator_ipv4_malware_neighborhood"}


def _load_candidate_node_scope_catalog() -> list[dict[str, object]]:
    if not FULL_SCOPE_CATALOG_PATH.is_file():
        raise AssertionError(f"Missing mirror sync full-scope catalog: {FULL_SCOPE_CATALOG_PATH}")

    payload = json.loads(FULL_SCOPE_CATALOG_PATH.read_text(encoding="utf-8"))
    candidate_node_scopes = payload.get("candidate_node_scopes")
    if not isinstance(candidate_node_scopes, list) or not candidate_node_scopes:
        raise AssertionError("Mirror sync full-scope catalog must define a non-empty candidate_node_scopes list")

    materialized_scopes: list[dict[str, object]] = []
    for index, scope in enumerate(candidate_node_scopes):
        if not isinstance(scope, dict):
            raise AssertionError(f"Invalid candidate node scope at index {index}: expected object")
        materialized_scope = dict(scope)
        materialized_scope["enabled"] = True
        materialized_scope.setdefault("required_for_baseline", False)
        materialized_scopes.append(materialized_scope)
    return materialized_scopes


def _materialize_node_scopes(payload: dict[str, object]) -> list[dict[str, object]]:
    enable_all_candidate_node_scopes = payload.get("enable_all_candidate_node_scopes", False)
    if not isinstance(enable_all_candidate_node_scopes, bool):
        raise AssertionError("Mirror sync scope config field 'enable_all_candidate_node_scopes' must be boolean")

    node_scopes = payload.get("node_scopes")
    if enable_all_candidate_node_scopes:
        explicit_scopes = node_scopes if isinstance(node_scopes, list) else []
        explicit_names = {
            str(scope.get("name", "")).strip()
            for scope in explicit_scopes
            if isinstance(scope, dict)
        }
        merged_scopes = list(explicit_scopes)
        for candidate_scope in _load_candidate_node_scope_catalog():
            candidate_name = str(candidate_scope.get("name", "")).strip()
            if candidate_name in explicit_names:
                continue
            merged_scopes.append(candidate_scope)
        return merged_scopes

    return node_scopes


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


def _sync_scope_hash() -> str:
    return hashlib.sha256(SYNC_SCOPE_PATH.read_bytes()).hexdigest()


def _load_sync_scope_config() -> dict[str, dict[str, dict[str, object]]]:
    if not SYNC_SCOPE_PATH.is_file():
        raise AssertionError(f"Missing mirror sync scope config: {SYNC_SCOPE_PATH}")

    payload = json.loads(SYNC_SCOPE_PATH.read_text(encoding="utf-8"))
    version = payload.get("version")
    if version != 1:
        raise AssertionError(f"Unsupported mirror sync scope config version: {version}")

    node_scopes = _materialize_node_scopes(payload)
    if not isinstance(node_scopes, list) or not node_scopes:
        raise AssertionError("Mirror sync scope config must define a non-empty node_scopes list")

    scopes_by_name: dict[str, dict[str, object]] = {}
    for index, scope in enumerate(node_scopes):
        if not isinstance(scope, dict):
            raise AssertionError(f"Invalid node scope at index {index}: expected object")
        name = str(scope.get("name", "")).strip()
        graphql_field = str(scope.get("graphql_field", "")).strip()
        selection = str(scope.get("selection", "")).strip()
        bootstrap_mode = str(scope.get("bootstrap_mode", "")).strip()
        enabled = scope.get("enabled")
        required_for_baseline = scope.get("required_for_baseline")

        if not name:
            raise AssertionError(f"Invalid node scope at index {index}: missing name")
        if name in scopes_by_name:
            raise AssertionError(f"Duplicate mirror sync node scope name: {name}")
        if not graphql_field:
            raise AssertionError(f"Mirror sync node scope '{name}' is missing graphql_field")
        if not selection:
            raise AssertionError(f"Mirror sync node scope '{name}' is missing selection")
        if bootstrap_mode not in {"incremental", "bootstrap_once"}:
            raise AssertionError(
                f"Mirror sync node scope '{name}' has unsupported bootstrap_mode '{bootstrap_mode}'"
            )
        projection = scope.get("projection")
        search = scope.get("search")
        if not isinstance(enabled, bool):
            raise AssertionError(f"Mirror sync node scope '{name}' must declare boolean enabled")
        if not isinstance(required_for_baseline, bool):
            raise AssertionError(
                f"Mirror sync node scope '{name}' must declare boolean required_for_baseline"
            )
        if required_for_baseline and not enabled:
            raise AssertionError(
                f"Mirror sync node scope '{name}' is required for the acceptance baseline and cannot be disabled"
            )
        if not isinstance(projection, dict):
            raise AssertionError(f"Mirror sync node scope '{name}' is missing projection")
        label = str(projection.get("label", "")).strip()
        merge_key = projection.get("merge_key")
        properties = projection.get("properties")
        if not label:
            raise AssertionError(f"Mirror sync node scope '{name}' projection is missing label")
        if not isinstance(merge_key, dict):
            raise AssertionError(f"Mirror sync node scope '{name}' projection is missing merge_key")
        if not str(merge_key.get("property", "")).strip() or not str(merge_key.get("source_field", "")).strip():
            raise AssertionError(f"Mirror sync node scope '{name}' projection has incomplete merge_key")
        if not isinstance(properties, list) or not properties:
            raise AssertionError(f"Mirror sync node scope '{name}' projection must define properties")
        for property_index, property_mapping in enumerate(properties):
            if not isinstance(property_mapping, dict):
                raise AssertionError(
                    f"Mirror sync node scope '{name}' has invalid property mapping at index {property_index}"
                )
            property_name = str(property_mapping.get("property", "")).strip()
            source_field = str(property_mapping.get("source_field", "")).strip()
            has_static_value = "static_value" in property_mapping
            if not property_name:
                raise AssertionError(
                    f"Mirror sync node scope '{name}' has property mapping without property name"
                )
            if not source_field and not has_static_value:
                raise AssertionError(
                    f"Mirror sync node scope '{name}' property '{property_name}' must define source_field or static_value"
                )
        if search is not None:
            if not isinstance(search, dict):
                raise AssertionError(f"Mirror sync node scope '{name}' search must be an object")
            mode = str(search.get("mode", "")).strip()
            search_field = str(search.get("search_field", "")).strip()
            if mode != "search_connection":
                raise AssertionError(f"Mirror sync node scope '{name}' has unsupported search mode '{mode}'")
            if not search_field:
                raise AssertionError(f"Mirror sync node scope '{name}' search is missing search_field")
        scopes_by_name[name] = dict(scope)

    missing_required_scopes = REQUIRED_NODE_SCOPE_NAMES - set(scopes_by_name)
    if missing_required_scopes:
        missing_names = ", ".join(sorted(missing_required_scopes))
        raise AssertionError(f"Mirror sync scope config is missing required node scopes: {missing_names}")

    relationship_scopes = payload.get("relationship_scopes")
    if not isinstance(relationship_scopes, list) or not relationship_scopes:
        raise AssertionError("Mirror sync scope config must define a non-empty relationship_scopes list")

    relationship_scopes_by_name: dict[str, dict[str, object]] = {}
    for index, scope in enumerate(relationship_scopes):
        if not isinstance(scope, dict):
            raise AssertionError(f"Invalid relationship scope at index {index}: expected object")
        name = str(scope.get("name", "")).strip()
        bootstrap_mode = str(scope.get("bootstrap_mode", "")).strip()
        enabled = scope.get("enabled")
        required_for_baseline = scope.get("required_for_baseline")
        source_node_scope = str(scope.get("source_node_scope", "")).strip()
        source_entity_type = str(scope.get("source_entity_type", "")).strip()
        via_relationships = scope.get("via_relationships")
        projection = scope.get("projection")
        projection_relationships = scope.get("projection_relationships")
        named_fallback = scope.get("named_fallback")
        participants = scope.get("participants")

        if not name:
            raise AssertionError(f"Invalid relationship scope at index {index}: missing name")
        if name in relationship_scopes_by_name:
            raise AssertionError(f"Duplicate mirror sync relationship scope name: {name}")
        if not isinstance(enabled, bool):
            raise AssertionError(f"Mirror sync relationship scope '{name}' must declare boolean enabled")
        if not isinstance(required_for_baseline, bool):
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' must declare boolean required_for_baseline"
            )
        if bootstrap_mode not in {"incremental", "bootstrap_once"}:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' has unsupported bootstrap_mode '{bootstrap_mode}'"
            )
        if required_for_baseline and not enabled:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' is required for the acceptance baseline and cannot be disabled"
            )
        if source_node_scope not in scopes_by_name:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' references unknown source_node_scope '{source_node_scope}'"
            )
        if not source_entity_type:
            raise AssertionError(f"Mirror sync relationship scope '{name}' is missing source_entity_type")
        if not isinstance(via_relationships, list) or len(via_relationships) < 2:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' must define at least two via_relationships"
            )
        for via_index, via in enumerate(via_relationships):
            if not isinstance(via, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' has invalid via_relationship at index {via_index}"
                )
            via_name = str(via.get("name", "")).strip()
            relationship_type = str(via.get("relationship_type", "")).strip()
            target_node_scope = str(via.get("target_node_scope", "")).strip()
            target_entity_type = str(via.get("target_entity_type", "")).strip()
            fallback_search = via.get("fallback_search")
            from_participant = str(via.get("from_participant", "")).strip()
            to_participant = str(via.get("to_participant", "")).strip()
            if not via_name or not relationship_type:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' has incomplete via_relationship at index {via_index}"
                )
            if target_node_scope not in scopes_by_name:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' references unknown target_node_scope '{target_node_scope}'"
                )
            if not target_entity_type:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' via_relationship '{via_name}' is missing target_entity_type"
                )
            if not from_participant or not to_participant:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' via_relationship '{via_name}' must define from_participant and to_participant"
                )
            if not isinstance(fallback_search, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' via_relationship '{via_name}' is missing fallback_search"
                )
            resolver = str(fallback_search.get("resolver", "")).strip()
            search_field = str(fallback_search.get("search_field", "")).strip()
            if resolver not in {"observable_by_value", "malware_by_name"}:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' via_relationship '{via_name}' has unsupported resolver '{resolver}'"
                )
            if search_field not in {"observable_value", "malware_name"}:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' via_relationship '{via_name}' has unsupported search_field '{search_field}'"
                )
        if not isinstance(participants, dict) or not participants:
            raise AssertionError(f"Mirror sync relationship scope '{name}' must define participants")
        for participant_name, participant in participants.items():
            if not isinstance(participant, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' has invalid participant '{participant_name}'"
                )
            node_scope_name = str(participant.get("node_scope", "")).strip()
            payload_prefix = str(participant.get("payload_prefix", "")).strip()
            if node_scope_name not in scopes_by_name:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' participant '{participant_name}' references unknown node scope '{node_scope_name}'"
                )
            if not payload_prefix:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' participant '{participant_name}' is missing payload_prefix"
                )
        if projection is not None:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' uses deprecated projection field; use projection_relationships"
            )
        if not isinstance(projection_relationships, list) or not projection_relationships:
            raise AssertionError(
                f"Mirror sync relationship scope '{name}' must define projection_relationships"
            )
        for projection_index, relationship_projection in enumerate(projection_relationships):
            if not isinstance(relationship_projection, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' has invalid projection_relationship at index {projection_index}"
                )
            relation_type = str(relationship_projection.get("type", "")).strip()
            kind = str(relationship_projection.get("kind", "")).strip()
            from_participant = str(relationship_projection.get("from_participant", "")).strip()
            to_participant = str(relationship_projection.get("to_participant", "")).strip()
            merge_key = relationship_projection.get("merge_key")
            properties = relationship_projection.get("properties")
            if kind not in {"upstream", "derived"}:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship has unsupported kind '{kind}'"
                )
            if not relation_type or not from_participant or not to_participant:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship is incomplete"
                )
            if from_participant not in participants or to_participant not in participants:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship references unknown participants"
                )
            if not isinstance(merge_key, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship is missing merge_key"
                )
            merge_property = str(merge_key.get("property", "")).strip()
            merge_source_field = str(merge_key.get("source_field", "")).strip()
            merge_key_format = str(merge_key.get("key_format", "")).strip()
            if not merge_property or (not merge_source_field and not merge_key_format):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship has incomplete merge_key"
                )
            if not isinstance(properties, list):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' projection relationship must define properties"
                )
        if not isinstance(named_fallback, dict) or not isinstance(named_fallback.get("enabled"), bool):
            raise AssertionError(f"Mirror sync relationship scope '{name}' is missing named_fallback")
        if named_fallback.get("enabled"):
            synthetic_relationship_ids = named_fallback.get("synthetic_relationship_ids")
            delimiter = str(named_fallback.get("indicator_name_delimiter", "")).strip()
            search_term = str(named_fallback.get("indicator_search_term", "")).strip()
            if not delimiter:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' named_fallback is missing indicator_name_delimiter"
                )
            if not search_term:
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' named_fallback is missing indicator_search_term"
                )
            if not isinstance(synthetic_relationship_ids, dict):
                raise AssertionError(
                    f"Mirror sync relationship scope '{name}' named_fallback is missing synthetic_relationship_ids"
                )
        relationship_scopes_by_name[name] = dict(scope)

    missing_relationship_scopes = REQUIRED_RELATIONSHIP_SCOPE_NAMES - set(relationship_scopes_by_name)
    if missing_relationship_scopes:
        missing_names = ", ".join(sorted(missing_relationship_scopes))
        raise AssertionError(f"Mirror sync scope config is missing required relationship scopes: {missing_names}")

    return {
        "node_scopes": scopes_by_name,
        "relationship_scopes": relationship_scopes_by_name,
    }


def _scope_since(
    *,
    state: dict[str, object],
    scope_name: str,
    bootstrapped_key: str,
    incremental_since: datetime,
    bootstrap_mode: str,
    config_changed: bool,
) -> datetime:
    if config_changed:
        bootstrap_since = _parse_timestamp(_bootstrap_floor())
        return bootstrap_since or incremental_since
    bootstrapped_scopes = {
        str(item)
        for item in state.get(bootstrapped_key, [])
        if isinstance(item, str)
    }
    if scope_name not in bootstrapped_scopes and bootstrap_mode in {"incremental", "bootstrap_once"}:
        bootstrap_since = _parse_timestamp(_bootstrap_floor())
        return bootstrap_since or incremental_since
    return incremental_since


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


def _fetch_recent_scope(scope: dict[str, object], since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        str(scope["graphql_field"]),
        str(scope["selection"]),
        since,
    )


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
    return _fetch_recent_scope(_load_sync_scope_config()["node_scopes"]["ipv4_observable"], since)


def _fetch_recent_indicators(since: datetime) -> list[dict[str, object]]:
    return _fetch_recent_scope(_load_sync_scope_config()["node_scopes"]["indicator"], since)


def _fetch_indicator_by_id(indicator_id: str) -> dict[str, object] | None:
    query = (
        "query MirrorIndicatorById($id: String!) {"
        " indicator(id: $id) {"
        "   id standard_id name pattern updated_at created_at x_opencti_main_observable_type"
        " }"
        "}"
    )
    try:
        data = _graphql_request(query, {"id": indicator_id})
    except AssertionError:
        return None
    indicator = data.get("indicator")
    if not isinstance(indicator, dict):
        return None
    return indicator


def _fetch_recent_malwares(since: datetime) -> list[dict[str, object]]:
    return _fetch_recent_scope(_load_sync_scope_config()["node_scopes"]["malware"], since)


def _fetch_recent_vulnerabilities(since: datetime) -> list[dict[str, object]]:
    return _fetch_recent_scope(_load_sync_scope_config()["node_scopes"]["vulnerability"], since)


def _fetch_recent_relationships(since: datetime) -> list[dict[str, object]]:
    return _fetch_connection(
        "stixCoreRelationships",
        "id standard_id relationship_type updated_at created_at from { ... on BasicObject { id standard_id entity_type } } to { ... on BasicObject { id standard_id entity_type } }",
        since,
    )


def _fetch_named_replica_indicators(since: datetime) -> list[dict[str, object]]:
    scopes = _load_sync_scope_config()
    relationship_scope = scopes["relationship_scopes"]["indicator_ipv4_malware_neighborhood"]
    selection = str(scopes["node_scopes"]["indicator"]["selection"])
    candidate_map: dict[str, dict[str, object]] = {}
    search_term = str(dict(relationship_scope["named_fallback"])["indicator_search_term"])

    for candidate in _search_connection("indicators", selection, search_term, limit=200):
        candidate_id = str(candidate.get("id", "")).strip()
        if candidate_id:
            candidate_map[candidate_id] = candidate

    return [
        candidate
        for candidate in candidate_map.values()
        if search_term in str(candidate.get("name", ""))
    ]


def _search_node_scope(scope_name: str, search_value: str, *, limit: int = 10) -> dict[str, object] | None:
    scope = _load_sync_scope_config()["node_scopes"][scope_name]
    search = dict(scope.get("search") or {})
    if not search:
        return None
    matches = _search_connection(
        str(scope["graphql_field"]),
        str(scope["selection"]),
        search_value,
        limit=limit,
    )
    match_fields = search.get("match_fields") or []
    for match in matches:
        if not match_fields:
            if match.get(search["search_field"]) == search_value:
                return match
            continue
        if all(
            match.get(str(field_rule["record_field"]))
            == (search_value if field_rule.get("equals_search") else field_rule.get("equals"))
            for field_rule in match_fields
        ):
            return match
    return None


def _fetch_observable_by_value(value: str) -> dict[str, object] | None:
    return _search_node_scope("ipv4_observable", value, limit=10)


def _fetch_malware_by_name(name: str) -> dict[str, object] | None:
    return _search_node_scope("malware", name, limit=10)


def _payload_source_value(record: dict[str, object], source_field: str, *, prefix: str | None = None) -> object:
    if prefix:
        return record.get(f"{prefix}_{source_field}")
    return record.get(source_field)


def _build_node_projection_parameters(
    node_scope: dict[str, object],
    record: dict[str, object],
    *,
    payload_prefix: str | None = None,
) -> tuple[str, str, dict[str, object]]:
    projection = dict(node_scope["projection"])
    merge_key = dict(projection["merge_key"])
    label = str(projection["label"])
    merge_property = str(merge_key["property"])
    merge_value = _payload_source_value(record, str(merge_key["source_field"]), prefix=payload_prefix)
    if merge_value in (None, ""):
        return label, merge_property, {}
    parameters: dict[str, object] = {"merge_value": merge_value}
    for property_mapping in projection["properties"]:
        property_name = str(property_mapping["property"])
        if "static_value" in property_mapping:
            parameters[property_name] = property_mapping.get("static_value")
        else:
            parameters[property_name] = _payload_source_value(
                record,
                str(property_mapping["source_field"]),
                prefix=payload_prefix,
            )
    return label, merge_property, parameters


def _project_node_scope_record(
    node_scope: dict[str, object],
    record: dict[str, object],
    *,
    payload_prefix: str | None = None,
) -> None:
    label, merge_property, parameters = _build_node_projection_parameters(
        node_scope,
        record,
        payload_prefix=payload_prefix,
    )
    if not parameters:
        return
    assignments = [
        f"node.{property_name} = ${property_name}"
        for property_name in parameters
        if property_name != "merge_value"
    ]
    statement = f"MERGE (node:`{label}` {{{merge_property}: $merge_value}})"
    if assignments:
        statement += " SET " + ", ".join(assignments)
    _run_cypher(statement, parameters)


def _project_relationship_payload(
    relationship_scope: dict[str, object],
    payload: dict[str, object],
    node_scopes: dict[str, dict[str, object]],
) -> None:
    participants = dict(relationship_scope["participants"])
    for participant in participants.values():
        node_scope = node_scopes[str(participant["node_scope"])]
        _project_node_scope_record(node_scope, payload, payload_prefix=str(participant["payload_prefix"]))

    for relationship_projection in relationship_scope["projection_relationships"]:
        from_participant = dict(participants[str(relationship_projection["from_participant"])])
        to_participant = dict(participants[str(relationship_projection["to_participant"])])
        from_scope = node_scopes[str(from_participant["node_scope"])]
        to_scope = node_scopes[str(to_participant["node_scope"])]
        from_projection = dict(from_scope["projection"])
        to_projection = dict(to_scope["projection"])
        from_merge_key = dict(from_projection["merge_key"])
        to_merge_key = dict(to_projection["merge_key"])
        from_key_value = _payload_source_value(
            payload,
            str(from_merge_key["source_field"]),
            prefix=str(from_participant["payload_prefix"]),
        )
        to_key_value = _payload_source_value(
            payload,
            str(to_merge_key["source_field"]),
            prefix=str(to_participant["payload_prefix"]),
        )
        if from_key_value in (None, "") or to_key_value in (None, ""):
            continue
        merge_key = dict(relationship_projection["merge_key"])
        merge_property = str(merge_key["property"])
        merge_source_field = str(merge_key.get("source_field", "")).strip()
        merge_value = payload.get(merge_source_field) if merge_source_field else None
        if not merge_value:
            key_format = str(merge_key.get("key_format", "")).strip()
            if key_format:
                merge_value = key_format.format(**payload)
        if not merge_value:
            continue
        parameters: dict[str, object] = {
            "from_key_value": from_key_value,
            "to_key_value": to_key_value,
            "relationship_merge_value": merge_value,
        }
        assignments: list[str] = []
        for property_mapping in relationship_projection.get("properties", []):
            property_name = str(property_mapping["property"])
            parameters[property_name] = (
                property_mapping.get("static_value")
                if "static_value" in property_mapping
                else payload.get(str(property_mapping["source_field"]))
            )
            assignments.append(f"relationship.{property_name} = ${property_name}")
        statement = (
            f"MERGE (source:`{from_projection['label']}` {{{from_merge_key['property']}: $from_key_value}}) "
            f"MERGE (target:`{to_projection['label']}` {{{to_merge_key['property']}: $to_key_value}}) "
            f"MERGE (source)-[relationship:`{relationship_projection['type']}` {{{merge_property}: $relationship_merge_value}}]->(target)"
        )
        if assignments:
            statement += " SET " + ", ".join(assignments)
        _run_cypher(statement, parameters)


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


def _relationship_key(merge_key: dict[str, object], payload: dict[str, object]) -> str:
    key_format = str(merge_key["key_format"])
    try:
        return key_format.format(**payload)
    except KeyError as exc:
        raise AssertionError(f"Missing key field for relationship projection: {exc.args[0]}") from exc


def _indicator_named_parts(
    indicator: dict[str, object],
    relationship_scope: dict[str, object],
) -> tuple[str | None, str | None]:
    indicator_name = str(indicator.get("name", "")).strip()
    delimiter = str(dict(relationship_scope["named_fallback"])["indicator_name_delimiter"])
    if delimiter not in indicator_name:
        return None, None
    malware_name, observable_value = indicator_name.rsplit(delimiter, 1)
    return malware_name, observable_value


def _indicator_ipv4_value(indicator: dict[str, object], relationship_scope: dict[str, object]) -> str | None:
    pattern = str(indicator.get("pattern", "")).strip()
    match = IPV4_PATTERN_RE.search(pattern)
    if match:
        return match.group(1)
    _, observable_value = _indicator_named_parts(indicator, relationship_scope)
    return observable_value


def _indicator_malware_name(indicator: dict[str, object], relationship_scope: dict[str, object]) -> str | None:
    malware_name, _ = _indicator_named_parts(indicator, relationship_scope)
    return malware_name


def _group_relationships_by_source(
    relationships: list[dict[str, object]],
    relationship_scope: dict[str, object],
) -> dict[str, dict[str, list[dict[str, object]]]]:
    grouped: dict[str, dict[str, list[dict[str, object]]]] = {}
    expected_source_entity_type = str(relationship_scope["source_entity_type"])
    allowed_relationship_types = {
        str(via_relationship["relationship_type"]): str(via_relationship["name"])
        for via_relationship in relationship_scope["via_relationships"]
    }
    for relationship in relationships:
        source = relationship.get("from") or {}
        source_id = str(source.get("id", "")).strip()
        relationship_type = str(relationship.get("relationship_type", "")).strip()
        if not source_id or source.get("entity_type") != expected_source_entity_type:
            continue
        if relationship_type not in allowed_relationship_types:
            continue
        via_name = allowed_relationship_types[relationship_type]
        grouped.setdefault(source_id, {}).setdefault(via_name, []).append(relationship)
    return grouped


def _search_value_for_via(
    indicator: dict[str, object],
    via_relationship: dict[str, object],
    relationship_scope: dict[str, object],
) -> str | None:
    fallback_search = dict(via_relationship["fallback_search"])
    search_field = str(fallback_search["search_field"])
    if search_field == "observable_value":
        return _indicator_ipv4_value(indicator, relationship_scope)
    if search_field == "malware_name":
        return _indicator_malware_name(indicator, relationship_scope)
    return None


def _resolve_via_target(
    *,
    indicator: dict[str, object],
    via_relationship: dict[str, object],
    relationship: dict[str, object],
    records_by_scope: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object] | None:
    relationship_target = relationship.get("to") or {}
    target_scope = str(via_relationship["target_node_scope"])
    record = records_by_scope.get(target_scope, {}).get(str(relationship_target.get("id", "")))
    if record is not None:
        return record
    if relationship_target.get("entity_type") != via_relationship.get("target_entity_type"):
        return None
    relationship_scope = _load_sync_scope_config()["relationship_scopes"]["indicator_ipv4_malware_neighborhood"]
    search_value = _search_value_for_via(indicator, via_relationship, relationship_scope)
    standard_id = relationship_target.get("standard_id")
    if not search_value:
        return None
    searched_record = _search_node_scope(target_scope, search_value, limit=10)
    if searched_record is not None:
        searched_standard_id = searched_record.get("standard_id")
        if not standard_id or searched_standard_id == standard_id:
            return searched_record
    if not standard_id:
        return None
    resolver = str(dict(via_relationship["fallback_search"])["resolver"])
    if resolver == "observable_by_value":
        return {
            "id": relationship_target.get("id"),
            "standard_id": standard_id,
            "entity_type": via_relationship.get("target_entity_type"),
            "value": search_value,
            "created_at": indicator.get("created_at"),
            "updated_at": indicator.get("updated_at"),
        }
    if resolver == "malware_by_name":
        return {
            "id": relationship_target.get("id"),
            "standard_id": standard_id,
            "name": search_value,
            "description": None,
            "revoked": None,
            "confidence": None,
            "created_at": indicator.get("created_at"),
            "updated_at": indicator.get("updated_at"),
        }
    return None


def _synthetic_relationship(
    template: str,
    indicator: dict[str, object],
    target: dict[str, object],
) -> dict[str, object]:
    return {
        "id": template.format(
            indicator_id=indicator["id"],
            observable_id=target.get("id"),
            malware_id=target.get("id"),
        ),
        "standard_id": None,
        "created_at": indicator.get("created_at"),
        "updated_at": indicator.get("updated_at"),
    }


def _relationship_projection_by_name(
    relationship_scope: dict[str, object],
    projection_name: str,
) -> dict[str, object]:
    for relationship_projection in relationship_scope["projection_relationships"]:
        if relationship_projection.get("name") == projection_name:
            return dict(relationship_projection)
    raise AssertionError(
        f"Mirror sync relationship scope '{relationship_scope['name']}' is missing projection relationship '{projection_name}'"
    )


def _pair_payload(
    *,
    relationship_scope: dict[str, object],
    observable: dict[str, object],
    indicator: dict[str, object],
    malware: dict[str, object],
    based_on_relationship: dict[str, object],
    indicates_relationship: dict[str, object],
) -> dict[str, object]:
    payload = {"relationship_scope_name": relationship_scope["name"]}
    participants = {
        "observable": observable,
        "indicator": indicator,
        "malware": malware,
    }
    for participant_name, participant_record in participants.items():
        for field_name, field_value in participant_record.items():
            payload[f"{participant_name}_{field_name}"] = field_value

    payload["based_on_relationship_id"] = based_on_relationship["id"]
    payload["based_on_standard_id"] = based_on_relationship.get("standard_id")
    payload["based_on_created_at"] = based_on_relationship.get("created_at")
    payload["based_on_updated_at"] = based_on_relationship.get("updated_at")
    payload["indicates_relationship_id"] = indicates_relationship["id"]
    payload["indicates_standard_id"] = indicates_relationship.get("standard_id")
    payload["indicates_created_at"] = indicates_relationship.get("created_at")
    payload["indicates_updated_at"] = indicates_relationship.get("updated_at")

    derived_projection = _relationship_projection_by_name(relationship_scope, "projected_indicates")
    payload["projected_relationship_type"] = derived_projection["type"]
    payload["projected_relationship_key"] = _relationship_key(dict(derived_projection["merge_key"]), payload)
    return payload


def _collect_candidate_pairs(
    *,
    relationship_scope: dict[str, object],
    observables: list[dict[str, object]],
    indicators: list[dict[str, object]],
    malwares: list[dict[str, object]],
    relationships: list[dict[str, object]],
    since: datetime,
    existing_pairs: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    indicators_by_id = {str(item["id"]): item for item in indicators if item.get("id")}
    participants = dict(relationship_scope["participants"])
    records_by_scope = {
        str(participants["observable"]["node_scope"]): {
            str(item["id"]): item for item in observables if item.get("id")
        },
        str(participants["indicator"]["node_scope"]): indicators_by_id,
        str(participants["malware"]["node_scope"]): {
            str(item["id"]): item for item in malwares if item.get("id")
        },
    }
    via_relationships = {
        str(via_relationship["name"]): dict(via_relationship)
        for via_relationship in relationship_scope["via_relationships"]
    }
    grouped_relationships = _group_relationships_by_source(relationships, relationship_scope)
    primary_via = via_relationships["based_on"]
    secondary_via = via_relationships["indicates"]

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
            indicator = _fetch_indicator_by_id(indicator_id)
            if indicator is not None:
                indicators_by_id[indicator_id] = indicator
        if indicator is None:
            continue
        relationships_by_name = grouped_relationships.get(indicator_id, {})
        for based_on_relationship in relationships_by_name.get("based_on", []):
            observable = _resolve_via_target(
                indicator=indicator,
                via_relationship=primary_via,
                relationship=based_on_relationship,
                records_by_scope=records_by_scope,
            )
            if observable is None:
                continue
            for indicates_relationship in relationships_by_name.get("indicates", []):
                malware = _resolve_via_target(
                    indicator=indicator,
                    via_relationship=secondary_via,
                    relationship=indicates_relationship,
                    records_by_scope=records_by_scope,
                )
                if malware is None:
                    continue
                pair = _pair_payload(
                    relationship_scope=relationship_scope,
                    observable=observable,
                    indicator=indicator,
                    malware=malware,
                    based_on_relationship=based_on_relationship,
                    indicates_relationship=indicates_relationship,
                )
                tracked_pairs[str(pair["projected_relationship_key"])] = pair

        if relationships_by_name.get("based_on"):
            continue

        if not dict(relationship_scope["named_fallback"]).get("enabled"):
            continue

        observable_value = _search_value_for_via(indicator, primary_via, relationship_scope)
        if not observable_value:
            continue
        observable = _fetch_observable_by_value(observable_value)
        if observable is None:
            continue
        synthetic_templates = dict(dict(relationship_scope["named_fallback"])["synthetic_relationship_ids"])
        for indicates_relationship in relationships_by_name.get("indicates", []):
            malware = _resolve_via_target(
                indicator=indicator,
                via_relationship=secondary_via,
                relationship=indicates_relationship,
                records_by_scope=records_by_scope,
            )
            if malware is None:
                continue
            pair = _pair_payload(
                relationship_scope=relationship_scope,
                observable=observable,
                indicator=indicator,
                malware=malware,
                based_on_relationship=_synthetic_relationship(
                    synthetic_templates["based_on"],
                    indicator,
                    observable,
                ),
                indicates_relationship=indicates_relationship,
            )
            tracked_pairs[str(pair["projected_relationship_key"])] = pair
    return tracked_pairs


def _collect_named_pairs(
    relationship_scope: dict[str, object],
    since: datetime,
    existing_pairs: dict[str, dict[str, object]],
) -> tuple[dict[str, dict[str, object]], list[str]]:
    tracked_pairs = dict(existing_pairs)
    matched_indicator_names: list[str] = []
    named_fallback = dict(relationship_scope["named_fallback"])
    if not named_fallback.get("enabled"):
        return tracked_pairs, matched_indicator_names
    delimiter = str(named_fallback["indicator_name_delimiter"])
    synthetic_templates = dict(named_fallback["synthetic_relationship_ids"])
    for indicator in _fetch_named_replica_indicators(since):
        indicator_name = str(indicator.get("name", "")).strip()
        if delimiter not in indicator_name:
            continue
        malware_name, ipv4_value = indicator_name.rsplit(delimiter, 1)
        observable = _fetch_observable_by_value(ipv4_value)
        malware = _fetch_malware_by_name(malware_name)
        if observable is None or malware is None:
            continue
        matched_indicator_names.append(indicator_name)
        payload = _pair_payload(
            relationship_scope=relationship_scope,
            observable=observable,
            indicator=indicator,
            malware=malware,
            based_on_relationship={
                "id": synthetic_templates["based_on"].format(
                    indicator_id=indicator["id"],
                    observable_id=observable["id"],
                    malware_id=malware["id"],
                ),
                "standard_id": None,
                "created_at": indicator.get("created_at"),
                "updated_at": indicator.get("updated_at"),
            },
            indicates_relationship={
                "id": synthetic_templates["indicates"].format(
                    indicator_id=indicator["id"],
                    observable_id=observable["id"],
                    malware_id=malware["id"],
                ),
                "standard_id": None,
                "created_at": indicator.get("created_at"),
                "updated_at": indicator.get("updated_at"),
            },
        )
        tracked_pairs[str(payload["projected_relationship_key"])] = payload
    return tracked_pairs, matched_indicator_names


def _project_pair(pair: dict[str, object]) -> None:
    scopes = _load_sync_scope_config()
    _project_relationship_payload(
        scopes["relationship_scopes"]["indicator_ipv4_malware_neighborhood"],
        pair,
        scopes["node_scopes"],
    )


def _project_vulnerability(vulnerability: dict[str, object]) -> None:
    _project_node_scope_record(_load_sync_scope_config()["node_scopes"]["vulnerability"], vulnerability)


def _enabled_scope_names(scopes_by_name: dict[str, dict[str, object]]) -> list[str]:
    return [name for name, scope in scopes_by_name.items() if scope.get("enabled")]


def _sync_cycle(state: dict[str, object]) -> dict[str, object]:
    scopes_by_name = _load_sync_scope_config()
    node_scopes = scopes_by_name["node_scopes"]
    relationship_scopes = scopes_by_name["relationship_scopes"]
    since = _effective_since(state)
    sync_scope_hash = _sync_scope_hash()
    config_changed = str(state.get("sync_scope_hash", "")) != sync_scope_hash

    records_by_scope: dict[str, list[dict[str, object]]] = {}
    scope_since_by_name: dict[str, str] = {}
    for scope_name, scope in node_scopes.items():
        if not scope.get("enabled"):
            records_by_scope[scope_name] = []
            continue
        scope_since = _scope_since(
            state=state,
            scope_name=scope_name,
            bootstrapped_key="bootstrapped_node_scopes",
            incremental_since=since,
            bootstrap_mode=str(scope["bootstrap_mode"]),
            config_changed=config_changed,
        )
        records = _fetch_recent_scope(scope, scope_since)
        records_by_scope[scope_name] = records
        scope_since_by_name[scope_name] = scope_since.astimezone(UTC).isoformat().replace("+00:00", "Z")
        for record in records:
            _project_node_scope_record(scope, record)

    relationships: list[dict[str, object]] = []
    relationship_scope_since = since
    relationship_scope = relationship_scopes["indicator_ipv4_malware_neighborhood"]
    if relationship_scope["enabled"]:
        relationship_scope_since = _scope_since(
            state=state,
            scope_name=str(relationship_scope["name"]),
            bootstrapped_key="bootstrapped_relationship_scopes",
            incremental_since=since,
            bootstrap_mode=str(relationship_scope["bootstrap_mode"]),
            config_changed=config_changed,
        )
        relationships = _fetch_recent_relationships(relationship_scope_since)

    existing_pairs = {} if config_changed else {
        str(pair["projected_relationship_key"]): pair
        for pair in state.get("tracked_pairs", [])
        if isinstance(pair, dict) and pair.get("projected_relationship_key")
    }
    tracked_pairs = (
        _collect_candidate_pairs(
            relationship_scope=relationship_scope,
            observables=records_by_scope.get("ipv4_observable", []),
            indicators=records_by_scope.get("indicator", []),
            malwares=records_by_scope.get("malware", []),
            relationships=relationships,
            since=relationship_scope_since,
            existing_pairs=existing_pairs,
        )
        if relationship_scope["enabled"]
        else existing_pairs
    )
    tracked_pairs, matched_indicator_names = _collect_named_pairs(
        relationship_scope,
        relationship_scope_since,
        tracked_pairs,
    )
    for pair in tracked_pairs.values():
        _project_relationship_payload(relationship_scope, pair, node_scopes)

    _write_discovery_debug(
        {
            "since": since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "config_changed": config_changed,
            "sync_scope_hash": sync_scope_hash,
            "scope_since_by_name": scope_since_by_name,
            "relationship_scope_since": relationship_scope_since.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "enabled_node_scopes": _enabled_scope_names(node_scopes),
            "enabled_relationship_scopes": _enabled_scope_names(relationship_scopes),
            "recent_indicator_names": [item.get("name") for item in records_by_scope.get("indicator", [])],
            "recent_vulnerability_names": [item.get("name") for item in records_by_scope.get("vulnerability", [])],
            "recent_relationship_types": [item.get("relationship_type") for item in relationships],
            "matched_indicator_names": matched_indicator_names,
            "tracked_pair_keys": sorted(tracked_pairs),
        }
    )

    next_state = {
        "backend": "neo4j-replica",
        "stream_id": os.getenv("STREAM_ID", "").strip(),
        "bootstrap_start_at": _read_anchor_timestamp(),
        "last_synced_at": _max_seen_timestamp(*records_by_scope.values(), relationships),
        "last_poll_at": _current_timestamp(),
        "sync_scope_hash": sync_scope_hash,
        "vulnerabilities_bootstrapped": bool(node_scopes["vulnerability"]["enabled"]),
        "bootstrapped_node_scopes": _enabled_scope_names(node_scopes),
        "bootstrapped_relationship_scopes": _enabled_scope_names(relationship_scopes),
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