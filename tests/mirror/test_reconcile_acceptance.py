from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from _fixture_support import ensure_mirror_seed_fixture, run_cypher


ROOT = Path(__file__).resolve().parent
RECONCILE_FIXTURE = ROOT / "protected_fixtures" / "reconcile_probe.md"
RECONCILE_BASELINE = ROOT / "protected_baselines" / "reconcile_contract.md"


def test_delete_and_revoke_semantics_align_in_replica() -> None:
    assert RECONCILE_FIXTURE.is_file(), "Protected reconcile fixture file is required"
    assert RECONCILE_BASELINE.is_file(), "Protected reconcile baseline file is required"

    suffix = uuid4().hex[:8]
    seed = ensure_mirror_seed_fixture(
        ipv4_value=f"1.2.7.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Reconcile-{suffix}",
    )

    run_cypher(
        (
            "MATCH (:`ipv4-addr` {standard_id: $observable_standard_id})-[r:indicates]->(:malware {name: $malware_name}) "
            "DELETE r"
        ),
        {
            "observable_standard_id": seed["ipv4_standard_id"],
            "malware_name": seed["malware_name"],
        },
    )
    time.sleep(5)

    relationship_rows = run_cypher(
        (
            "MATCH (:`ipv4-addr` {standard_id: $observable_standard_id})-[r:indicates]->(:malware {name: $malware_name}) "
            "RETURN count(r) AS relationship_count"
        ),
        {
            "observable_standard_id": seed["ipv4_standard_id"],
            "malware_name": seed["malware_name"],
        },
    )
    assert relationship_rows[0]["relationship_count"] == 1, "Reconcile must repair drifted replica relationships after they go missing"