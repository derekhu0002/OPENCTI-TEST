from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import _fixture_support as fixture_support


def test_mirror_fixture_support_contracts_require_real_environment_path() -> None:
    root = Path(__file__).resolve().parent
    fixture_text = (root / "protected_fixtures" / "bootstrap_window_probe.md").read_text(encoding="utf-8")
    incremental_text = (root / "protected_baselines" / "live_incremental_contract.md").read_text(encoding="utf-8")
    reconcile_text = (root / "protected_baselines" / "reconcile_contract.md").read_text(encoding="utf-8")

    assert "bootstrap start anchor" in fixture_text
    assert "must not import or call mirror-sync internals" in fixture_text
    assert "not by direct test-side calls into mirror-sync" in incremental_text
    assert "must not shortcut the repair by importing or invoking mirror-sync internals" in reconcile_text


def test_bootstrap_and_projection_acceptance_require_freshness_and_watermark_evidence() -> None:
    root = Path(__file__).resolve().parent
    bootstrap_text = (root / "test_bootstrap_window_acceptance.py").read_text(encoding="utf-8")
    projection_text = (root / "test_projection_policy_acceptance.py").read_text(encoding="utf-8")

    assert "load_freshness" in bootstrap_text
    assert "load_watermark_artifacts" in bootstrap_text
    assert "load_freshness" in projection_text
    assert "load_watermark_artifacts" in projection_text


def test_reconcile_acceptance_induces_drift_without_direct_sync_shortcut() -> None:
    reconcile_text = (Path(__file__).resolve().parent / "test_reconcile_acceptance.py").read_text(encoding="utf-8")

    assert "DELETE r" in reconcile_text
    assert "sync_hot_subgraph" not in reconcile_text
    assert "importlib.util" not in reconcile_text
    assert "mirror-sync" not in reconcile_text


def test_mirror_auto_seed_support_returns_expected_fixture_shape(prepared_mirror_seed: dict[str, str]) -> None:
    assert prepared_mirror_seed["ipv4_value"] == os.getenv("MIRROR_EXPECTED_IPV4_VALUE", "1.2.3.4")
    assert prepared_mirror_seed["malware_name"] == os.getenv("MIRROR_EXPECTED_MALWARE_NAME", "Mirai-Botnet")
    assert prepared_mirror_seed["ipv4_standard_id"]
    assert prepared_mirror_seed["bootstrap_start_at"].endswith("Z")
    assert prepared_mirror_seed["relationship_type"] == "indicates"

    anchor_path = Path(__file__).resolve().parents[2] / "mirror-sync" / "runtime" / "test_bootstrap_anchor.json"
    assert anchor_path.is_file()
    anchor_payload = json.loads(anchor_path.read_text(encoding="utf-8"))
    assert anchor_payload["bootstrap_start_at"] == prepared_mirror_seed["bootstrap_start_at"]


def test_wait_for_replica_projection_requires_indicates_relationship(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIRROR_ASSERT_TIMEOUT_SECONDS", "2")

    tick = {"value": -1}

    def fake_time() -> int:
        tick["value"] += 1
        return tick["value"]

    monkeypatch.setattr(fixture_support.time, "time", fake_time)
    monkeypatch.setattr(fixture_support.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        fixture_support,
        "run_cypher",
        lambda _statement, _parameters: [{
            "observable_standard_id": "observable-1",
            "malware_standard_id": "malware-1",
            "relation_type": None,
        }],
    )
    monkeypatch.setattr(fixture_support, "load_freshness", lambda: {"sync_status": "healthy"})
    monkeypatch.setattr(fixture_support, "load_watermark_artifacts", lambda: [Path("runtime/test.watermark")])

    with pytest.raises(AssertionError, match="Timed out waiting for real mirror replica projection"):
        fixture_support._wait_for_replica_projection(
            observable_standard_id="observable-1",
            malware_standard_id="malware-1",
        )


def test_wait_for_replica_projection_requires_watermark_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIRROR_ASSERT_TIMEOUT_SECONDS", "2")

    tick = {"value": -1}

    def fake_time() -> int:
        tick["value"] += 1
        return tick["value"]

    monkeypatch.setattr(fixture_support.time, "time", fake_time)
    monkeypatch.setattr(fixture_support.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        fixture_support,
        "run_cypher",
        lambda _statement, _parameters: [{
            "observable_standard_id": "observable-1",
            "malware_standard_id": "malware-1",
            "relation_type": "indicates",
        }],
    )
    monkeypatch.setattr(fixture_support, "load_freshness", lambda: {"sync_status": "healthy"})
    monkeypatch.setattr(fixture_support, "load_watermark_artifacts", lambda: [])

    with pytest.raises(AssertionError, match="Timed out waiting for real mirror replica projection"):
        fixture_support._wait_for_replica_projection(
            observable_standard_id="observable-1",
            malware_standard_id="malware-1",
        )


def test_wait_for_replica_projection_accepts_relation_freshness_and_watermark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIRROR_ASSERT_TIMEOUT_SECONDS", "2")
    monkeypatch.setattr(fixture_support.time, "time", lambda: 0)
    monkeypatch.setattr(fixture_support.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        fixture_support,
        "run_cypher",
        lambda _statement, _parameters: [{
            "observable_standard_id": "observable-1",
            "malware_standard_id": "malware-1",
            "relation_type": "indicates",
        }],
    )
    monkeypatch.setattr(fixture_support, "load_freshness", lambda: {"sync_status": "healthy"})
    monkeypatch.setattr(fixture_support, "load_watermark_artifacts", lambda: [Path("runtime/test.watermark")])

    fixture_support._wait_for_replica_projection(
        observable_standard_id="observable-1",
        malware_standard_id="malware-1",
    )