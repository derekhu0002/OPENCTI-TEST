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


def test_effective_since_rewinds_existing_watermark() -> None:
    since = service._effective_since({"last_synced_at": "2026-05-14T12:00:05Z"})

    expected_recent_floor = datetime.now(UTC) - service.timedelta(minutes=service.RECENT_LOOKBACK_MINUTES)
    assert since <= expected_recent_floor
    assert since >= expected_recent_floor - service.timedelta(seconds=2)


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