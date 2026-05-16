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
    connection_arguments: dict[str, object] | None = None,
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
    if connection_arguments is not None:
        payload["connection_arguments"] = connection_arguments
    return payload


def _sample_relationship_scope() -> dict[str, object]:
    return {
        "name": "indicator_ipv4_malware_neighborhood",
        "enabled": True,
        "required_for_baseline": True,
        "bootstrap_mode": "incremental",
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


def _sample_direct_relationship_scope() -> dict[str, object]:
    return {
        "name": "threat_intel_context_direct_relationships",
        "relationship_mode": "direct",
        "enabled": True,
        "required_for_baseline": False,
        "bootstrap_mode": "incremental",
        "allowed_relationship_types": ["indicates", "uses", "targets", "related-to", "mitigates"],
        "entity_type_node_scopes": {
            "Indicator": "indicator",
            "Malware": "malware",
            "Attack-Pattern": "attackPatterns",
            "Infrastructure": "infrastructures",
            "Intrusion-Set": "intrusionSets",
            "Campaign": "campaigns",
            "Identity": "identities",
            "Sector": "sectors",
            "Course-Of-Action": "coursesOfAction",
            "Observed-Data": "observedData",
            "Report": "reports",
            "Grouping": "groupings",
            "Tool": "tools",
            "Vulnerability": "vulnerability",
        },
        "relationship_projection": {
            "merge_key": {
                "property": "opencti_id",
                "source_field": "relationship_id",
            },
            "properties": [
                {"property": "standard_id", "source_field": "relationship_standard_id"},
                {"property": "relationship_type", "source_field": "relationship_type"},
                {"property": "created_at", "source_field": "relationship_created_at"},
                {"property": "updated_at", "source_field": "relationship_updated_at"},
            ],
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


def test_load_sync_scope_config_rejects_candidate_relationship_autoload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "version": 1,
        "enable_all_candidate_relationship_scopes": True,
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
        "relationship_scopes": [_sample_relationship_scope()],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    with pytest.raises(AssertionError, match="does not support enabling candidate relationship scopes automatically"):
        service._load_sync_scope_config()


def test_load_sync_scope_config_accepts_direct_relationship_scope(monkeypatch: pytest.MonkeyPatch) -> None:
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
            _sample_node_scope(
                "attackPatterns",
                required_for_baseline=False,
                graphql_field="attackPatterns",
                bootstrap_mode="bootstrap_once",
                label="attackPatterns",
                entity_type="Attack-Pattern",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "infrastructures",
                required_for_baseline=False,
                graphql_field="infrastructures",
                bootstrap_mode="bootstrap_once",
                label="infrastructures",
                entity_type="Infrastructure",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "intrusionSets",
                required_for_baseline=False,
                graphql_field="intrusionSets",
                bootstrap_mode="bootstrap_once",
                label="intrusionSets",
                entity_type="Intrusion-Set",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "campaigns",
                required_for_baseline=False,
                graphql_field="campaigns",
                bootstrap_mode="bootstrap_once",
                label="campaigns",
                entity_type="Campaign",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "identities",
                required_for_baseline=False,
                graphql_field="identities",
                bootstrap_mode="bootstrap_once",
                label="identities",
                entity_type="Identity",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "sectors",
                required_for_baseline=False,
                graphql_field="sectors",
                bootstrap_mode="bootstrap_once",
                label="sectors",
                entity_type="Sector",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "coursesOfAction",
                required_for_baseline=False,
                graphql_field="coursesOfAction",
                bootstrap_mode="bootstrap_once",
                label="coursesOfAction",
                entity_type="Course-Of-Action",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "observedData",
                required_for_baseline=False,
                graphql_field="observedData",
                bootstrap_mode="bootstrap_once",
                label="observedData",
                entity_type="Observed-Data",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "reports",
                required_for_baseline=False,
                graphql_field="reports",
                bootstrap_mode="bootstrap_once",
                label="reports",
                entity_type="Report",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "groupings",
                required_for_baseline=False,
                graphql_field="groupings",
                bootstrap_mode="bootstrap_once",
                label="groupings",
                entity_type="Grouping",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            _sample_node_scope(
                "tools",
                required_for_baseline=False,
                graphql_field="tools",
                bootstrap_mode="bootstrap_once",
                label="tools",
                entity_type="Tool",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
        ],
        "relationship_scopes": [_sample_relationship_scope(), _sample_direct_relationship_scope()],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    scopes = service._load_sync_scope_config()

    assert "threat_intel_context_direct_relationships" in scopes["relationship_scopes"]


def test_fetch_connection_paginates_all_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        {
            "attackPatterns": {
                "edges": [{"node": {"id": "attack-pattern-1"}}, {"node": {"id": "attack-pattern-2"}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
            }
        },
        {
            "attackPatterns": {
                "edges": [{"node": {"id": "attack-pattern-3"}}],
                "pageInfo": {"hasNextPage": False, "endCursor": "cursor-2"},
            }
        },
    ]
    graphql_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(service, "_configured_graphql_page_size", lambda: 2)

    def _fake_graphql_request(query: str, variables: dict[str, object] | None = None) -> dict[str, object]:
        graphql_calls.append((query, dict(variables or {})))
        return responses[len(graphql_calls) - 1]

    monkeypatch.setattr(service, "_graphql_request", _fake_graphql_request)

    records = service._fetch_connection(
        "attackPatterns",
        "id standard_id name updated_at created_at",
        datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
    )

    assert [record["id"] for record in records] == [
        "attack-pattern-1",
        "attack-pattern-2",
        "attack-pattern-3",
    ]
    assert graphql_calls[0][1]["first"] == 2
    assert graphql_calls[0][1]["after"] is None
    assert graphql_calls[1][1]["after"] == "cursor-1"


def test_sync_cycle_projects_direct_relationship_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    projected_relationships: list[tuple[str, dict[str, object]]] = []

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
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "attackPatterns": _sample_node_scope(
            "attackPatterns",
            required_for_baseline=False,
            graphql_field="attackPatterns",
            bootstrap_mode="bootstrap_once",
            label="attackPatterns",
            entity_type="Attack-Pattern",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "infrastructures": _sample_node_scope(
            "infrastructures",
            required_for_baseline=False,
            graphql_field="infrastructures",
            bootstrap_mode="bootstrap_once",
            label="infrastructures",
            entity_type="Infrastructure",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "intrusionSets": _sample_node_scope(
            "intrusionSets",
            required_for_baseline=False,
            graphql_field="intrusionSets",
            bootstrap_mode="bootstrap_once",
            label="intrusionSets",
            entity_type="Intrusion-Set",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "campaigns": _sample_node_scope(
            "campaigns",
            required_for_baseline=False,
            graphql_field="campaigns",
            bootstrap_mode="bootstrap_once",
            label="campaigns",
            entity_type="Campaign",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "identities": _sample_node_scope(
            "identities",
            required_for_baseline=False,
            graphql_field="identities",
            bootstrap_mode="bootstrap_once",
            label="identities",
            entity_type="Identity",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "sectors": _sample_node_scope(
            "sectors",
            required_for_baseline=False,
            graphql_field="sectors",
            bootstrap_mode="bootstrap_once",
            label="sectors",
            entity_type="Sector",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "coursesOfAction": _sample_node_scope(
            "coursesOfAction",
            required_for_baseline=False,
            graphql_field="coursesOfAction",
            bootstrap_mode="bootstrap_once",
            label="coursesOfAction",
            entity_type="Course-Of-Action",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "observedData": _sample_node_scope(
            "observedData",
            required_for_baseline=False,
            graphql_field="observedData",
            bootstrap_mode="bootstrap_once",
            label="observedData",
            entity_type="Observed-Data",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "reports": _sample_node_scope(
            "reports",
            required_for_baseline=False,
            graphql_field="reports",
            bootstrap_mode="bootstrap_once",
            label="reports",
            entity_type="Report",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "groupings": _sample_node_scope(
            "groupings",
            required_for_baseline=False,
            graphql_field="groupings",
            bootstrap_mode="bootstrap_once",
            label="groupings",
            entity_type="Grouping",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "tools": _sample_node_scope(
            "tools",
            required_for_baseline=False,
            graphql_field="tools",
            bootstrap_mode="bootstrap_once",
            label="tools",
            entity_type="Tool",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
    }

    baseline_scope = _sample_relationship_scope()
    baseline_scope["enabled"] = False

    monkeypatch.setattr(service, "_effective_since", lambda state: since)
    monkeypatch.setattr(service, "_sync_scope_hash", lambda: "scope-hash-1")
    monkeypatch.setattr(
        service,
        "_load_sync_scope_config",
        lambda: {
            "node_scopes": node_scopes,
            "relationship_scopes": {
                "indicator_ipv4_malware_neighborhood": baseline_scope,
                "threat_intel_context_direct_relationships": _sample_direct_relationship_scope(),
            },
        },
    )
    monkeypatch.setattr(service, "_fetch_recent_scope", lambda scope, query_since: [])
    monkeypatch.setattr(
        service,
        "_fetch_recent_relationships",
        lambda _: [
            {
                "id": "relationship-1",
                "standard_id": "relationship--1",
                "relationship_type": "uses",
                "created_at": "2026-05-14T12:00:04Z",
                "updated_at": "2026-05-14T12:00:05Z",
                "from": {
                    "id": "intrusion-set-1",
                    "standard_id": "intrusion-set--1",
                    "entity_type": "Intrusion-Set",
                },
                "to": {
                    "id": "malware-1",
                    "standard_id": "malware--1",
                    "entity_type": "Malware",
                },
            }
        ],
    )
    monkeypatch.setattr(service, "_collect_candidate_pairs", lambda **_: {})
    monkeypatch.setattr(service, "_collect_named_pairs", lambda _, __, tracked_pairs: (tracked_pairs, []))
    monkeypatch.setattr(service, "_project_node_scope_record", lambda scope, record, payload_prefix=None: None)
    monkeypatch.setattr(
        service,
        "_project_relationship_payload",
        lambda relationship_scope, payload, scopes: projected_relationships.append((str(relationship_scope["name"]), payload)),
    )
    monkeypatch.setattr(service, "_write_discovery_debug", lambda payload: None)
    monkeypatch.setattr(service, "_persist_watermark_state", lambda state: None)
    monkeypatch.setattr(service, "_current_timestamp", lambda: "2026-05-14T12:00:09Z")
    monkeypatch.setattr(service, "_read_anchor_timestamp", lambda: "")

    service._sync_cycle({"tracked_pairs": []})

    assert projected_relationships == [
        (
            "threat_intel_context_direct_relationships",
            {
                "relationship_scope_name": "threat_intel_context_direct_relationships",
                "source_node_scope": "intrusionSets",
                "target_node_scope": "malware",
                "source_id": "intrusion-set-1",
                "source_standard_id": "intrusion-set--1",
                "source_entity_type": "Intrusion-Set",
                "target_id": "malware-1",
                "target_standard_id": "malware--1",
                "target_entity_type": "Malware",
                "relationship_id": "relationship-1",
                "relationship_standard_id": "relationship--1",
                "relationship_type": "uses",
                "relationship_created_at": "2026-05-14T12:00:04Z",
                "relationship_updated_at": "2026-05-14T12:00:05Z",
            },
        )
    ]


def test_fetch_connection_passes_observable_type_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    graphql_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(service, "_configured_graphql_page_size", lambda: 50)

    def _fake_graphql_request(query: str, variables: dict[str, object] | None = None) -> dict[str, object]:
        graphql_calls.append((query, dict(variables or {})))
        return {
            "stixCyberObservables": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    monkeypatch.setattr(service, "_graphql_request", _fake_graphql_request)

    service._fetch_connection(
        "stixCyberObservables",
        "id standard_id entity_type observable_value updated_at created_at",
        datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC),
        {"types": ["Domain-Name"]},
    )

    assert "types: $types" in graphql_calls[0][0]
    assert graphql_calls[0][1]["types"] == ["Domain-Name"]


def test_load_sync_scope_config_accepts_typed_connection_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
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
            _sample_node_scope(
                "domain_name_observable",
                required_for_baseline=False,
                graphql_field="stixCyberObservables",
                selection="id standard_id entity_type observable_value updated_at created_at",
                bootstrap_mode="bootstrap_once",
                label="domain-name",
                entity_type="Domain-Name",
                extra_properties=[{"property": "value", "source_field": "observable_value"}],
                search={
                    "mode": "search_connection",
                    "search_field": "observable_value",
                    "match_fields": [
                        {"record_field": "entity_type", "equals": "Domain-Name"},
                        {"record_field": "observable_value", "equals_search": True},
                    ],
                },
                connection_arguments={"types": ["Domain-Name"]},
            ),
        ],
        "relationship_scopes": [_sample_relationship_scope()],
    }

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service.Path, "is_file", lambda self: True)
    monkeypatch.setattr(service.Path, "read_text", lambda self, encoding="utf-8": service.json.dumps(payload))

    scopes = service._load_sync_scope_config()

    assert scopes["node_scopes"]["domain_name_observable"]["connection_arguments"] == {"types": ["Domain-Name"]}


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


def test_load_sync_scope_config_can_enable_all_candidate_node_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "version": 1,
        "enable_all_candidate_node_scopes": True,
        "node_scopes": [
            _sample_node_scope(
                "ipv4_observable",
                graphql_field="stixCyberObservables",
                label="ipv4-addr",
                entity_type="IPv4-Addr",
                extra_properties=[{"property": "value", "source_field": "value"}],
                search={"mode": "search_connection", "search_field": "value"},
            )
        ],
        "relationship_scopes": [_sample_relationship_scope()],
    }
    candidate_scopes = [
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
        _sample_node_scope(
            "report",
            required_for_baseline=False,
            graphql_field="reports",
            bootstrap_mode="bootstrap_once",
            label="report",
            entity_type="Report",
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        {
            **_sample_node_scope(
                "about",
                required_for_baseline=False,
                graphql_field="about",
                bootstrap_mode="bootstrap_once",
                label="about",
                entity_type="AppInfo",
                extra_properties=[{"property": "name", "source_field": "name"}],
                search={"mode": "search_connection", "search_field": "name"},
            ),
            "introspection": {
                "return_type": "AppInfo",
                "arguments": [],
            },
        },
    ]

    candidate_scopes[0]["introspection"] = {"return_type": "IndicatorConnection", "arguments": ["first", "search"]}
    candidate_scopes[1]["introspection"] = {"return_type": "MalwareConnection", "arguments": ["first", "search"]}
    candidate_scopes[2]["introspection"] = {"return_type": "VulnerabilityConnection", "arguments": ["first", "search"]}
    candidate_scopes[3]["introspection"] = {"return_type": "ReportConnection", "arguments": ["first", "search"]}

    monkeypatch.setattr(service, "SYNC_SCOPE_PATH", Path("virtual/sync_scope.json"))
    monkeypatch.setattr(service, "FULL_SCOPE_CATALOG_PATH", Path("virtual/sync_scope.full.json"))
    monkeypatch.setattr(
        service,
        "_resolve_candidate_connection_node_metadata",
        lambda return_type: {
            "IndicatorConnection": ("Indicator", {"id", "standard_id", "entity_type", "created_at", "updated_at", "name"}),
            "MalwareConnection": ("Malware", {"id", "standard_id", "entity_type", "created_at", "updated_at", "name"}),
            "VulnerabilityConnection": ("Vulnerability", {"id", "standard_id", "entity_type", "created_at", "updated_at", "name"}),
            "ReportConnection": ("Report", {"id", "standard_id", "entity_type", "created_at", "updated_at", "name"}),
        }.get(return_type),
    )

    def _fake_is_file(self: Path) -> bool:
        return str(self) in {"virtual\\sync_scope.json", "virtual\\sync_scope.full.json"}

    def _fake_read_text(self: Path, encoding: str = "utf-8") -> str:
        if str(self) == "virtual\\sync_scope.json":
            return service.json.dumps(payload)
        if str(self) == "virtual\\sync_scope.full.json":
            return service.json.dumps({"candidate_node_scopes": candidate_scopes})
        raise AssertionError(f"Unexpected read_text path: {self}")

    monkeypatch.setattr(service.Path, "is_file", _fake_is_file)
    monkeypatch.setattr(service.Path, "read_text", _fake_read_text)

    scopes = service._load_sync_scope_config()

    assert {"ipv4_observable", "indicator", "malware", "vulnerability", "report"} <= set(scopes["node_scopes"])
    assert "about" not in scopes["node_scopes"]
    assert scopes["node_scopes"]["report"]["enabled"] is True
    assert set(scopes["relationship_scopes"]) == {"indicator_ipv4_malware_neighborhood"}


def test_materialize_candidate_node_scope_uses_available_connection_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        service,
        "_resolve_candidate_connection_node_metadata",
        lambda return_type: ("Log", {"id", "created_at"}) if return_type == "LogConnection" else None,
    )

    scope = service._materialize_candidate_node_scope(
        {
            **_sample_node_scope(
                "logs",
                required_for_baseline=False,
                graphql_field="logs",
                bootstrap_mode="bootstrap_once",
                label="logs",
                entity_type="Log",
                extra_properties=[{"property": "name", "source_field": "name"}],
            ),
            "introspection": {
                "return_type": "LogConnection",
                "arguments": ["first"],
            },
        }
    )

    assert scope is not None
    assert scope["selection"] == "id created_at"
    assert scope["projection"]["merge_key"]["source_field"] == "id"
    assert scope["projection"]["properties"] == [
        {"property": "opencti_id", "source_field": "id"},
        {"property": "entity_type", "static_value": "Log"},
        {"property": "created_at", "source_field": "created_at"},
    ]


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
    persisted_states: list[dict[str, object]] = []
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
    monkeypatch.setattr(service, "_persist_watermark_state", lambda state: persisted_states.append(state))
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
    assert persisted_states[0]["bootstrapped_node_scopes"] == []
    assert persisted_states[0]["tracked_pairs"] == []
    assert persisted_states[-1]["bootstrapped_node_scopes"] == [
        "ipv4_observable",
        "indicator",
        "malware",
        "vulnerability",
    ]
    assert debug_payloads[0]["enabled_node_scopes"] == ["ipv4_observable", "indicator", "malware", "vulnerability"]
    assert debug_payloads[0]["enabled_relationship_scopes"] == ["indicator_ipv4_malware_neighborhood"]
    assert debug_payloads[0]["scope_since_by_name"]["vulnerability"] == "2026-05-01T00:00:00Z"
    assert debug_payloads[0]["recent_vulnerability_names"] == ["CVE-2019-1132"]


def test_sync_cycle_skips_unsupported_optional_node_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 5, 14, 12, 0, 0, tzinfo=UTC)
    debug_payloads: list[dict[str, object]] = []
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
            extra_properties=[{"property": "name", "source_field": "name"}],
            search={"mode": "search_connection", "search_field": "name"},
        ),
        "disseminationLists": _sample_node_scope(
            "disseminationLists",
            enabled=True,
            required_for_baseline=False,
            graphql_field="disseminationLists",
            bootstrap_mode="bootstrap_once",
            label="disseminationLists",
            entity_type="DisseminationList",
            extra_properties=[{"property": "name", "source_field": "name"}],
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

    def _fake_fetch_recent_scope(scope: dict[str, object], query_since: datetime) -> list[dict[str, object]]:
        if scope["name"] == "disseminationLists":
            raise AssertionError("Enterprise edition is not enabled")
        return []

    monkeypatch.setattr(service, "_fetch_recent_scope", _fake_fetch_recent_scope)
    monkeypatch.setattr(service, "_fetch_recent_relationships", lambda _: [])
    monkeypatch.setattr(service, "_collect_candidate_pairs", lambda **_: {})
    monkeypatch.setattr(service, "_collect_named_pairs", lambda _, __, tracked_pairs: (tracked_pairs, []))
    monkeypatch.setattr(service, "_project_node_scope_record", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_project_relationship_payload", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_write_discovery_debug", lambda payload: debug_payloads.append(payload))
    monkeypatch.setattr(service, "_persist_watermark_state", lambda state: None)
    monkeypatch.setattr(service, "_read_anchor_timestamp", lambda: "")
    monkeypatch.setattr(service, "_current_timestamp", lambda: "2026-05-14T12:00:09Z")

    next_state = service._sync_cycle({"tracked_pairs": []})

    assert next_state["bootstrapped_node_scopes"] == [
        "ipv4_observable",
        "indicator",
        "malware",
        "vulnerability",
        "disseminationLists",
    ]
    assert debug_payloads[0]["skipped_optional_node_scope_errors"] == {
        "disseminationLists": "Enterprise edition is not enabled"
    }