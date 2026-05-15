from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "service.py"
SPEC = importlib.util.spec_from_file_location("mirror_sync_service", SERVICE_PATH)
assert SPEC is not None and SPEC.loader is not None
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)


def _sample_node_scope(
    name: str,
    *,
    enabled: bool = True,
    required_for_baseline: bool = True,
    graphql_field: str,
    selection: str = "id standard_id updated_at created_at",
    bootstrap_mode: str = "incremental",
    label: str,
    entity_type: str,
    extra_properties: list[dict[str, object]] | None = None,
    search: dict[str, object] | None = None,
) -> dict[str, object]:
    properties: list[dict[str, object]] = [
        {"property": "opencti_id", "source_field": "id"},
        {"property": "entity_type", "static_value": entity_type},
        {"property": "created_at", "source_field": "created_at"},
        {"property": "updated_at", "source_field": "updated_at"},
    ]
    if extra_properties:
        properties[2:2] = extra_properties
    payload: dict[str, object] = {
        "name": name,
        "enabled": enabled,
        "required_for_baseline": required_for_baseline,
        "graphql_field": graphql_field,
        "selection": selection,
        "bootstrap_mode": bootstrap_mode,
        "projection": {
            "label": label,
            "merge_key": {
                "property": "standard_id",
                "source_field": "standard_id",
            },
            "properties": properties,
        },
    }
    if search is not None:
        payload["search"] = search
    return payload


def _sample_relationship_scope() -> dict[str, object]:
    return {
        "name": "indicator_ipv4_malware_neighborhood",
        "enabled": True,
        "required_for_baseline": True,
        "source_node_scope": "indicator",
        "source_entity_type": "Indicator",
        "participants": {
            "observable": {
                "node_scope": "ipv4_observable",
                "payload_prefix": "observable",
            },
            "indicator": {
                "node_scope": "indicator",
                "payload_prefix": "indicator",
            },
            "malware": {
                "node_scope": "malware",
                "payload_prefix": "malware",
            },
        },
        "via_relationships": [
            {
                "name": "based_on",
                "relationship_type": "based-on",
                "from_participant": "indicator",
                "to_participant": "observable",
                "target_node_scope": "ipv4_observable",
                "target_entity_type": "IPv4-Addr",
                "fallback_search": {
                    "search_field": "observable_value",
                    "resolver": "observable_by_value",
                },
            },
            {
                "name": "indicates",
                "relationship_type": "indicates",
                "from_participant": "indicator",
                "to_participant": "malware",
                "target_node_scope": "malware",
                "target_entity_type": "Malware",
                "fallback_search": {
                    "search_field": "malware_name",
                    "resolver": "malware_by_name",
                },
            },
        ],
        "projection_relationships": [
            {
                "name": "based_on",
                "kind": "upstream",
                "from_participant": "indicator",
                "to_participant": "observable",
                "type": "based-on",
                "merge_key": {
                    "property": "opencti_id",
                    "source_field": "based_on_relationship_id",
                },
                "properties": [
                    {"property": "standard_id", "source_field": "based_on_standard_id"},
                    {"property": "relationship_type", "static_value": "based-on"},
                    {"property": "created_at", "source_field": "based_on_created_at"},
                    {"property": "updated_at", "source_field": "based_on_updated_at"},
                ],
            },
            {
                "name": "indicates",
                "kind": "upstream",
                "from_participant": "indicator",
                "to_participant": "malware",
                "type": "indicates",
                "merge_key": {
                    "property": "opencti_id",
                    "source_field": "indicates_relationship_id",
                },
                "properties": [
                    {"property": "standard_id", "source_field": "indicates_standard_id"},
                    {"property": "relationship_type", "static_value": "indicates"},
                    {"property": "created_at", "source_field": "indicates_created_at"},
                    {"property": "updated_at", "source_field": "indicates_updated_at"},
                ],
            },
            {
                "name": "projected_indicates",
                "kind": "derived",
                "from_participant": "observable",
                "to_participant": "malware",
                "type": "indicates",
                "merge_key": {
                    "property": "relationship_key",
                    "key_format": "{observable_standard_id}|{malware_standard_id}",
                },
                "properties": [
                    {"property": "relationship_type", "static_value": "indicates"},
                ],
            },
        ],
        "named_fallback": {
            "enabled": True,
            "indicator_search_term": " indicator for ",
            "indicator_name_delimiter": " indicator for ",
            "synthetic_relationship_ids": {
                "based_on": "search-based-on::{indicator_id}::{observable_id}",
                "indicates": "search-indicates::{indicator_id}::{malware_id}",
            },
        },
    }


def test_load_sync_scope_config_returns_required_node_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "version": 1,
        "node_scopes": [
            _sample_node_scope(
                "ipv4_observable",
                graphql_field="stixCyberObservables",
                label="ipv4-addr",
                entity_type="IPv4-Addr",
                extra_properties=[{"property": "value", "source_field": "value"}],
                search={
                    "mode": "search_connection",
                    "search_field": "value",
                    "match_fields": [
                        {"record_field": "entity_type", "equals": "IPv4-Addr"},
                        {"record_field": "value", "equals_search": True},
                    ],
                },
            ),
            _sample_node_scope(
                "indicator",
                graphql_field="indicators",
                label="indicator",
                entity_type="Indicator",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "malware",
                graphql_field="malwares",
                label="malware",
                entity_type="Malware",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "vulnerability",
                required_for_baseline=False,
                graphql_field="vulnerabilities",
                bootstrap_mode="bootstrap_once",
                label="vulnerability",
                entity_type="Vulnerability",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
        ],
        "relationship_scopes": [_sample_relationship_scope()],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    scopes = service._load_sync_scope_config()

    assert set(scopes["node_scopes"]) == {"ipv4_observable", "indicator", "malware", "vulnerability"}
    assert scopes["node_scopes"]["vulnerability"]["bootstrap_mode"] == "bootstrap_once"
    assert set(scopes["relationship_scopes"]) == {"indicator_ipv4_malware_neighborhood"}


def test_load_sync_scope_config_rejects_disabled_required_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "version": 1,
        "node_scopes": [
            _sample_node_scope(
                "ipv4_observable",
                enabled=False,
                graphql_field="stixCyberObservables",
                label="ipv4-addr",
                entity_type="IPv4-Addr",
                extra_properties=[{"property": "value", "source_field": "value"}],
                search={"mode": "search_connection", "search_field": "value"},
            ),
            _sample_node_scope(
                "indicator",
                graphql_field="indicators",
                label="indicator",
                entity_type="Indicator",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "malware",
                graphql_field="malwares",
                label="malware",
                entity_type="Malware",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "vulnerability",
                required_for_baseline=False,
                graphql_field="vulnerabilities",
                bootstrap_mode="bootstrap_once",
                label="vulnerability",
                entity_type="Vulnerability",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
        ],
        "relationship_scopes": [_sample_relationship_scope()],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    with pytest.raises(AssertionError, match="required for the acceptance baseline"):
        service._load_sync_scope_config()


def test_load_sync_scope_config_rejects_disabled_required_relationship_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    relationship_scope = _sample_relationship_scope()
    relationship_scope["enabled"] = False

    payload = {
        "version": 1,
        "node_scopes": [
            _sample_node_scope(
                "ipv4_observable",
                graphql_field="stixCyberObservables",
                label="ipv4-addr",
                entity_type="IPv4-Addr",
                extra_properties=[{"property": "value", "source_field": "value"}],
                search={"mode": "search_connection", "search_field": "value"},
            ),
            _sample_node_scope(
                "indicator",
                graphql_field="indicators",
                label="indicator",
                entity_type="Indicator",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "malware",
                graphql_field="malwares",
                label="malware",
                entity_type="Malware",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "vulnerability",
                required_for_baseline=False,
                graphql_field="vulnerabilities",
                bootstrap_mode="bootstrap_once",
                label="vulnerability",
                entity_type="Vulnerability",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
        ],
        "relationship_scopes": [relationship_scope],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    with pytest.raises(AssertionError, match="relationship scope 'indicator_ipv4_malware_neighborhood' is required"):
        service._load_sync_scope_config()


def test_effective_since_rewinds_existing_watermark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "_read_anchor_timestamp", lambda: "")

    since = service._effective_since({"last_synced_at": "2026-05-14T12:00:05Z"})

    assert since == datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)


def test_effective_since_resets_to_new_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "_read_anchor_timestamp", lambda: "2026-05-14T12:34:56Z")

    since = service._effective_since({
        "bootstrap_start_at": "2026-05-14T12:30:00Z",
        "last_synced_at": "2026-05-14T12:40:00Z",
    })

    assert since == datetime(2026, 5, 14, 12, 34, 56, tzinfo=UTC)


def test_updated_since_filters_use_gt_operator() -> None:
    since = datetime(2026, 5, 14, 12, 34, 56, tzinfo=UTC)

    payload = service._updated_since_filters(since)

    assert payload["mode"] == "and"
    assert payload["filters"][0]["key"] == "updated_at"
    assert payload["filters"][0]["operator"] == "gt"
    assert payload["filters"][0]["values"] == ["2026-05-14T12:34:56Z"]


def test_collect_candidate_pairs_tracks_ipv4_indicator_malware_chain() -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    observables = [
        {
            "id": "observable-1",
            "standard_id": "ipv4-addr--1",
            "entity_type": "IPv4-Addr",
            "value": "1.2.3.4",
            "created_at": "2026-05-14T12:00:01Z",
            "updated_at": "2026-05-14T12:00:01Z",
        }
    ]
    indicators = [
        {
            "id": "indicator-1",
            "standard_id": "indicator--1",
            "name": "indicator",
            "pattern": "[ipv4-addr:value = '1.2.3.4']",
            "x_opencti_main_observable_type": "IPv4-Addr",
            "created_at": "2026-05-14T12:00:02Z",
            "updated_at": "2026-05-14T12:00:02Z",
        }
    ]
    malwares = [
        {
            "id": "malware-1",
            "standard_id": "malware--1",
            "name": "Mirai-Botnet",
            "description": "desc",
            "revoked": False,
            "confidence": 100,
            "created_at": "2026-05-14T12:00:03Z",
            "updated_at": "2026-05-14T12:00:03Z",
        }
    ]
    relationships = [
        {
            "id": "rel-based-on",
            "standard_id": "relationship--based-on",
            "relationship_type": "based-on",
            "created_at": "2026-05-14T12:00:04Z",
            "updated_at": "2026-05-14T12:00:04Z",
            "from": {"id": "indicator-1", "entity_type": "Indicator"},
            "to": {"id": "observable-1", "entity_type": "IPv4-Addr"},
        },
        {
            "id": "rel-indicates",
            "standard_id": "relationship--indicates",
            "relationship_type": "indicates",
            "created_at": "2026-05-14T12:00:05Z",
            "updated_at": "2026-05-14T12:00:05Z",
            "from": {"id": "indicator-1", "entity_type": "Indicator"},
            "to": {"id": "malware-1", "entity_type": "Malware"},
        },
    ]

    tracked_pairs = service._collect_candidate_pairs(
        relationship_scope=_sample_relationship_scope(),
        observables=observables,
        indicators=indicators,
        malwares=malwares,
        relationships=relationships,
        since=since,
        existing_pairs={},
    )

    assert list(tracked_pairs) == ["ipv4-addr--1|malware--1"]
    pair = tracked_pairs["ipv4-addr--1|malware--1"]
    assert pair["observable_value"] == "1.2.3.4"
    assert pair["indicator_standard_id"] == "indicator--1"
    assert pair["malware_name"] == "Mirai-Botnet"
    assert pair["based_on_relationship_id"] == "rel-based-on"
    assert pair["indicates_relationship_id"] == "rel-indicates"


def test_collect_candidate_pairs_falls_back_to_relationship_targets_for_non_recent_seed() -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    indicators = [
        {
            "id": "indicator-1",
            "standard_id": "indicator--1",
            "name": "Mirai-Botnet indicator for 1.2.3.4",
            "pattern": "[ipv4-addr:value = '1.2.3.4']",
            "x_opencti_main_observable_type": "IPv4-Addr",
            "created_at": "2026-05-14T12:00:02Z",
            "updated_at": "2026-05-14T12:00:02Z",
        }
    ]
    relationships = [
        {
            "id": "rel-based-on",
            "standard_id": "relationship--based-on",
            "relationship_type": "based-on",
            "created_at": "2026-05-14T12:00:04Z",
            "updated_at": "2026-05-14T12:00:04Z",
            "from": {"id": "indicator-1", "entity_type": "Indicator"},
            "to": {
                "id": "observable-1",
                "standard_id": "ipv4-addr--fixed",
                "entity_type": "IPv4-Addr",
            },
        },
        {
            "id": "rel-indicates",
            "standard_id": "relationship--indicates",
            "relationship_type": "indicates",
            "created_at": "2026-05-14T12:00:05Z",
            "updated_at": "2026-05-14T12:00:05Z",
            "from": {"id": "indicator-1", "entity_type": "Indicator"},
            "to": {
                "id": "malware-1",
                "standard_id": "malware--fixed",
                "entity_type": "Malware",
            },
        },
    ]

    tracked_pairs = service._collect_candidate_pairs(
        relationship_scope=_sample_relationship_scope(),
        observables=[],
        indicators=indicators,
        malwares=[],
        relationships=relationships,
        since=since,
        existing_pairs={},
    )

    assert list(tracked_pairs) == ["ipv4-addr--fixed|malware--fixed"]
    pair = tracked_pairs["ipv4-addr--fixed|malware--fixed"]
    assert pair["observable_value"] == "1.2.3.4"
    assert pair["observable_standard_id"] == "ipv4-addr--fixed"
    assert pair["malware_name"] == "Mirai-Botnet"
    assert pair["malware_standard_id"] == "malware--fixed"


def test_collect_candidate_pairs_fetches_non_recent_indicator_for_recent_indicates(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(
        service,
        "_fetch_indicator_by_id",
        lambda indicator_id: {
            "id": indicator_id,
            "standard_id": "indicator--1",
            "name": "Mirai-Botnet indicator for 1.2.3.4",
            "pattern": "[ipv4-addr:value = '1.2.3.4']",
            "x_opencti_main_observable_type": "IPv4-Addr",
            "created_at": "2026-05-14T12:00:02Z",
            "updated_at": "2026-05-14T12:00:02Z",
        },
    )
    monkeypatch.setattr(
        service,
        "_fetch_observable_by_value",
        lambda value: {
            "id": "observable-1",
            "standard_id": "ipv4-addr--fixed",
            "entity_type": "IPv4-Addr",
            "value": value,
            "created_at": "2026-05-14T12:00:01Z",
            "updated_at": "2026-05-14T12:00:01Z",
        },
    )
    relationships = [
        {
            "id": "rel-indicates",
            "standard_id": "relationship--indicates",
            "relationship_type": "indicates",
            "created_at": "2026-05-14T12:00:05Z",
            "updated_at": "2026-05-14T12:00:05Z",
            "from": {"id": "indicator-1", "entity_type": "Indicator"},
            "to": {
                "id": "malware-1",
                "standard_id": "malware--fixed",
                "entity_type": "Malware",
            },
        },
    ]

    tracked_pairs = service._collect_candidate_pairs(
        relationship_scope=_sample_relationship_scope(),
        observables=[],
        indicators=[],
        malwares=[],
        relationships=relationships,
        since=since,
        existing_pairs={},
    )

    assert list(tracked_pairs) == ["ipv4-addr--fixed|malware--fixed"]
    pair = tracked_pairs["ipv4-addr--fixed|malware--fixed"]
    assert pair["indicator_name"] == "Mirai-Botnet indicator for 1.2.3.4"
    assert pair["based_on_relationship_id"] == "search-based-on::indicator-1::observable-1"
    assert pair["indicates_relationship_id"] == "rel-indicates"


def test_project_vulnerability_merges_vulnerability_node(monkeypatch: pytest.MonkeyPatch) -> None:
    cypher_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(
        service,
        "_load_sync_scope_config",
        lambda: {
            "node_scopes": {
                "vulnerability": _sample_node_scope(
                    "vulnerability",
                    required_for_baseline=False,
                    graphql_field="vulnerabilities",
                    bootstrap_mode="bootstrap_once",
                    label="vulnerability",
                    entity_type="Vulnerability",
                    extra_properties=[
                        {"property": "name", "source_field": "name"},
                        {"property": "description", "source_field": "description"},
                    ],
                    search={"mode": "search_connection", "search_field": "name"},
                )
            },
            "relationship_scopes": {},
        },
    )

    monkeypatch.setattr(
        service,
        "_run_cypher",
        lambda statement, parameters: cypher_calls.append((statement, parameters)),
    )

    service._project_vulnerability(
        {
            "id": "vulnerability-1",
            "standard_id": "vulnerability--1",
            "name": "CVE-2019-1132",
            "description": "Test vulnerability",
            "created_at": "2026-05-14T12:00:01Z",
            "updated_at": "2026-05-14T12:00:02Z",
        }
    )

    assert len(cypher_calls) == 1
    statement, parameters = cypher_calls[0]
    assert "MERGE (node:`vulnerability` {standard_id: $merge_value})" in statement
    assert parameters["name"] == "CVE-2019-1132"
    assert parameters["merge_value"] == "vulnerability--1"


def test_sync_cycle_projects_recent_vulnerabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    projected_nodes: list[tuple[str, dict[str, object]]] = []
    projected_relationships: list[dict[str, object]] = []
    debug_payloads: list[dict[str, object]] = []
    fetch_scope_calls: list[tuple[str, datetime]] = []
    node_scopes = {
        "ipv4_observable": _sample_node_scope(
            "ipv4_observable",
            graphql_field="stixCyberObservables",
            label="ipv4-addr",
            entity_type="IPv4-Addr",
            extra_properties=[{"property": "value", "source_field": "value"}],
            search={"mode": "search_connection", "search_field": "value"},
        ),
        "indicator": _sample_node_scope(
            "indicator",
            graphql_field="indicators",
            label="indicator",
            entity_type="Indicator",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "malware": _sample_node_scope(
            "malware",
            graphql_field="malwares",
            label="malware",
            entity_type="Malware",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "vulnerability": _sample_node_scope(
            "vulnerability",
            required_for_baseline=False,
            graphql_field="vulnerabilities",
            bootstrap_mode="bootstrap_once",
            label="vulnerability",
            entity_type="Vulnerability",
            extra_properties=[
                {"property": "name", "source_field": "name"},
                {"property": "description", "source_field": "description"},
            ],
            search={"mode": "search_connection", "search_field": "name"},
        ),
    }

    monkeypatch.setattr(service, "_effective_since", lambda state: since)
    monkeypatch.setattr(service, "_sync_scope_hash", lambda: "scope-hash-1")
    monkeypatch.setattr(
        service,
        "_load_sync_scope_config",
        lambda: {
            "node_scopes": node_scopes,
            "relationship_scopes": {
                "indicator_ipv4_malware_neighborhood": _sample_relationship_scope(),
            },
        },
    )
    monkeypatch.setattr(service, "_bootstrap_floor", lambda: "2026-05-01T00:00:00Z")
    monkeypatch.setattr(
        service,
        "_fetch_recent_scope",
        lambda scope, query_since: fetch_scope_calls.append((str(scope["name"]), query_since))
        or (
            [
                {
                    "id": "vulnerability-1",
                    "standard_id": "vulnerability--1",
                    "name": "CVE-2019-1132",
                    "description": "Test vulnerability",
                    "created_at": "2026-05-14T12:00:01Z",
                    "updated_at": "2026-05-14T12:00:06Z",
                }
            ]
            if scope["name"] == "vulnerability"
            else []
        ),
    )
    monkeypatch.setattr(service, "_fetch_recent_relationships", lambda _: [])
    monkeypatch.setattr(service, "_collect_candidate_pairs", lambda **_: {})
    monkeypatch.setattr(service, "_collect_named_pairs", lambda _, __, tracked_pairs: (tracked_pairs, []))
    monkeypatch.setattr(
        service,
        "_project_node_scope_record",
        lambda scope, record, payload_prefix=None: projected_nodes.append((str(scope["name"]), record)),
    )
    monkeypatch.setattr(
        service,
        "_project_relationship_payload",
        lambda relationship_scope, pair, scopes: projected_relationships.append(pair),
    )
    monkeypatch.setattr(service, "_write_discovery_debug", lambda payload: debug_payloads.append(payload))
    monkeypatch.setattr(service, "_persist_watermark_state", lambda state: None)
    monkeypatch.setattr(service, "_read_anchor_timestamp", lambda: "")
    monkeypatch.setattr(service, "_current_timestamp", lambda: "2026-05-14T12:00:09Z")

    next_state = service._sync_cycle({"tracked_pairs": []})

    assert projected_relationships == []
    assert projected_nodes == [
        (
            "vulnerability",
            {
                "id": "vulnerability-1",
                "standard_id": "vulnerability--1",
                "name": "CVE-2019-1132",
                "description": "Test vulnerability",
                "created_at": "2026-05-14T12:00:01Z",
                "updated_at": "2026-05-14T12:00:06Z",
            },
        )
    ]
    assert fetch_scope_calls[3] == ("vulnerability", datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC))
    assert next_state["last_synced_at"] == "2026-05-14T12:00:06Z"
    assert next_state["vulnerabilities_bootstrapped"] is True
    assert next_state["sync_scope_hash"] == "scope-hash-1"
    assert next_state["bootstrapped_node_scopes"] == ["ipv4_observable", "indicator", "malware", "vulnerability"]
    assert debug_payloads[0]["enabled_node_scopes"] == ["ipv4_observable", "indicator", "malware", "vulnerability"]
    assert debug_payloads[0]["enabled_relationship_scopes"] == ["indicator_ipv4_malware_neighborhood"]
    assert debug_payloads[0]["scope_since_by_name"]["vulnerability"] == "2026-05-01T00:00:00Z"
    assert debug_payloads[0]["recent_vulnerability_names"] == ["CVE-2019-1132"]