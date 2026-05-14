from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from _fixture_support import ensure_mirror_seed_fixture, load_freshness, load_watermark_artifacts, run_cypher


ROOT = Path(__file__).resolve().parent
BOOTSTRAP_FIXTURE = ROOT / "protected_fixtures" / "bootstrap_window_probe.md"
BOOTSTRAP_BASELINE = ROOT / "protected_baselines" / "bootstrap_window_contract.md"


def test_default_one_year_window_syncs_changed_hot_subgraph() -> None:
    assert BOOTSTRAP_FIXTURE.is_file(), "Protected bootstrap fixture file is required"
    assert BOOTSTRAP_BASELINE.is_file(), "Protected bootstrap baseline file is required"

    suffix = uuid4().hex[:8]
    seed = ensure_mirror_seed_fixture(
        ipv4_value=f"1.2.3.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Bootstrap-{suffix}",
    )

    freshness = load_freshness()
    watermark_artifacts = load_watermark_artifacts()
    assert freshness["sync_status"] == "healthy"
    assert watermark_artifacts, "Bootstrap sync must expose durable watermark evidence alongside freshness"

    rows = run_cypher(
        (
            "MATCH (malware:malware {standard_id: $malware_standard_id}) "
            "RETURN malware.standard_id AS standard_id, malware.updated_at AS updated_at"
        ),
        {"malware_standard_id": seed["malware_standard_id"]},
    )
    assert rows, "Bootstrap sync must materialize the in-scope malware node"
    assert rows[0]["updated_at"], "Bootstrap sync must preserve updated_at for window-bound replica scope"


def test_two_hop_neighborhood_completion_preserves_direction() -> None:
    assert BOOTSTRAP_FIXTURE.is_file(), "Protected bootstrap fixture file is required"
    assert BOOTSTRAP_BASELINE.is_file(), "Protected bootstrap baseline file is required"

    suffix = uuid4().hex[:8]
    seed = ensure_mirror_seed_fixture(
        ipv4_value=f"1.2.4.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Neighborhood-{suffix}",
    )
    freshness = load_freshness()
    watermark_artifacts = load_watermark_artifacts()

    based_on_rows = run_cypher(
        (
            "MATCH (indicator:indicator {standard_id: $indicator_standard_id})-[r]->(observable:`ipv4-addr` {standard_id: $observable_standard_id}) "
            "RETURN type(r) AS relation_type LIMIT 1"
        ),
        {
            "indicator_standard_id": seed["indicator_standard_id"],
            "observable_standard_id": seed["ipv4_standard_id"],
        },
    )
    indicates_rows = run_cypher(
        (
            "MATCH (indicator:indicator {standard_id: $indicator_standard_id})-[r]->(malware:malware {name: $malware_name}) "
            "RETURN type(r) AS relation_type LIMIT 1"
        ),
        {
            "indicator_standard_id": seed["indicator_standard_id"],
            "malware_name": seed["malware_name"],
        },
    )

    assert freshness["sync_status"] == "healthy"
    assert watermark_artifacts, "Neighborhood completion acceptance requires watermark evidence from the real sync path"
    assert based_on_rows, "Two-hop neighborhood completion must retain the indicator-to-observable hop"
    assert based_on_rows[0]["relation_type"] == "based-on"
    assert indicates_rows, "Two-hop neighborhood completion must retain the indicator-to-malware hop"
    assert indicates_rows[0]["relation_type"] == "indicates"