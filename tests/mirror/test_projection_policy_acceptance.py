from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from _fixture_support import ensure_mirror_seed_fixture, load_freshness, load_watermark_artifacts, run_cypher


ROOT = Path(__file__).resolve().parent
PROJECTION_FIXTURE = ROOT / "protected_fixtures" / "projection_policy_probe.md"
PROJECTION_BASELINE = ROOT / "protected_baselines" / "projection_policy_contract.md"


def test_property_names_and_default_baseline_are_preserved() -> None:
    assert PROJECTION_FIXTURE.is_file(), "Protected projection fixture file is required"
    assert PROJECTION_BASELINE.is_file(), "Protected projection baseline file is required"

    suffix = uuid4().hex[:8]
    seed = ensure_mirror_seed_fixture(
        ipv4_value=f"1.2.6.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Projection-{suffix}",
    )
    freshness = load_freshness()
    watermark_artifacts = load_watermark_artifacts()

    malware_rows = run_cypher(
        (
            "MATCH (malware:malware {standard_id: $malware_standard_id}) "
            "RETURN malware.name AS name, malware.description AS description, "
            "malware.opencti_id AS opencti_id, malware.standard_id AS standard_id"
        ),
        {"malware_standard_id": seed["malware_standard_id"]},
    )
    relationship_rows = run_cypher(
        (
            "MATCH (:`ipv4-addr` {standard_id: $observable_standard_id})-[r:indicates]->(:malware {name: $malware_name}) "
            "RETURN r.relationship_type AS relationship_type, r.projected_via AS projected_via LIMIT 1"
        ),
        {
            "observable_standard_id": seed["ipv4_standard_id"],
            "malware_name": seed["malware_name"],
        },
    )

    assert freshness["sync_status"] == "healthy"
    assert watermark_artifacts, "Projection policy acceptance requires watermark evidence from the real sync path"
    assert malware_rows, "Projection policy acceptance requires the synchronized malware node"
    assert malware_rows[0]["name"] == seed["malware_name"]
    assert malware_rows[0]["description"] == seed["malware_description"]
    assert malware_rows[0]["opencti_id"]
    assert malware_rows[0]["standard_id"]
    assert relationship_rows, "Projection policy acceptance requires the synchronized relationship"
    assert relationship_rows[0]["relationship_type"] == "indicates"
    assert relationship_rows[0]["projected_via"] is None, "Replica relationships must not expose local alias properties instead of upstream field names"