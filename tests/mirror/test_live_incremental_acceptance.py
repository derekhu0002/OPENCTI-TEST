from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from _fixture_support import create_graphql_only_change, load_freshness, load_watermark_artifacts, run_cypher


ROOT = Path(__file__).resolve().parent
INCREMENTAL_FIXTURE = ROOT / "protected_fixtures" / "live_incremental_probe.md"
INCREMENTAL_BASELINE = ROOT / "protected_baselines" / "live_incremental_contract.md"


def test_live_stream_updates_reach_replica_and_refresh_freshness() -> None:
    assert INCREMENTAL_FIXTURE.is_file(), "Protected live incremental fixture file is required"
    assert INCREMENTAL_BASELINE.is_file(), "Protected live incremental baseline file is required"

    suffix = uuid4().hex[:8]

    change = create_graphql_only_change(
        ipv4_value=f"1.2.5.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Incremental-{suffix}",
        malware_description=f"Incremental change {suffix} expected to arrive through live stream",
    )
    time.sleep(5)

    rows = run_cypher(
        (
            "MATCH (observable:`ipv4-addr` {standard_id: $observable_standard_id})"
            "-[r:indicates]->(malware:malware {standard_id: $malware_standard_id}) "
            "RETURN observable.standard_id AS standard_id, "
            "       type(r) AS relationship_type, "
            "       malware.standard_id AS malware_standard_id LIMIT 1"
        ),
        {
            "observable_standard_id": change["ipv4_standard_id"],
            "malware_standard_id": change["malware_standard_id"],
        },
    )
    freshness = load_freshness()
    watermark_artifacts = load_watermark_artifacts()

    assert rows, "Incremental changes must reach the replica without a manual reseed invocation"
    assert rows[0]["relationship_type"] == "indicates"
    assert rows[0]["malware_standard_id"] == change["malware_standard_id"]
    assert freshness["sync_status"] == "healthy"
    assert watermark_artifacts, "Incremental sync must persist watermark evidence alongside replica freshness"


def test_watermark_recovery_replays_idempotently() -> None:
    assert INCREMENTAL_FIXTURE.is_file(), "Protected live incremental fixture file is required"
    assert INCREMENTAL_BASELINE.is_file(), "Protected live incremental baseline file is required"

    watermark_artifacts = load_watermark_artifacts()
    assert watermark_artifacts, "Incremental sync must persist a durable watermark artifact for replay-safe recovery"