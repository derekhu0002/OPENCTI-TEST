from __future__ import annotations

import json
import traceback
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tests' / 'mirror'))

from _fixture_support import create_graphql_only_change, ensure_mirror_seed_fixture, load_freshness, load_watermark_artifacts, run_cypher  # noqa: E402


results: dict[str, object] = {}

suffix = uuid4().hex[:8]
try:
    seed = ensure_mirror_seed_fixture(
        ipv4_value=f"1.2.3.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Bootstrap-{suffix}",
    )
    freshness = load_freshness()
    watermark_artifacts = [str(path) for path in load_watermark_artifacts()]
    malware_rows = run_cypher(
        "MATCH (malware:malware {standard_id: $malware_standard_id}) RETURN malware.standard_id AS standard_id, malware.updated_at AS updated_at",
        {"malware_standard_id": seed["malware_standard_id"]},
    )
    based_on_rows = run_cypher(
        "MATCH (indicator:indicator {standard_id: $indicator_standard_id})-[r]->(observable:`ipv4-addr` {standard_id: $observable_standard_id}) RETURN type(r) AS relation_type LIMIT 1",
        {"indicator_standard_id": seed["indicator_standard_id"], "observable_standard_id": seed["ipv4_standard_id"]},
    )
    indicates_rows = run_cypher(
        "MATCH (indicator:indicator {standard_id: $indicator_standard_id})-[r]->(malware:malware {name: $malware_name}) RETURN type(r) AS relation_type LIMIT 1",
        {"indicator_standard_id": seed["indicator_standard_id"], "malware_name": seed["malware_name"]},
    )
    results['bootstrap'] = {
        'ok': True,
        'seed': seed,
        'freshness': freshness,
        'watermark_artifacts': watermark_artifacts,
        'malware_rows': malware_rows,
        'based_on_rows': based_on_rows,
        'indicates_rows': indicates_rows,
    }
except Exception:
    results['bootstrap'] = {
        'ok': False,
        'traceback': traceback.format_exc(),
    }

suffix = uuid4().hex[:8]
try:
    change = create_graphql_only_change(
        ipv4_value=f"1.2.5.{int(suffix[:2], 16) % 200 + 20}",
        malware_name=f"Replica-Incremental-{suffix}",
        malware_description=f"Incremental change {suffix} expected to arrive through live stream",
    )
    rows = run_cypher(
        "MATCH (observable:`ipv4-addr` {standard_id: $observable_standard_id})-[r:indicates]->(malware:malware {standard_id: $malware_standard_id}) RETURN observable.standard_id AS standard_id, type(r) AS relationship_type, malware.standard_id AS malware_standard_id LIMIT 1",
        {"observable_standard_id": change["ipv4_standard_id"], "malware_standard_id": change["malware_standard_id"]},
    )
    results['incremental'] = {
        'ok': True,
        'change': change,
        'rows': rows,
        'freshness': load_freshness(),
        'watermark_artifacts': [str(path) for path in load_watermark_artifacts()],
    }
except Exception:
    results['incremental'] = {
        'ok': False,
        'traceback': traceback.format_exc(),
    }

(ROOT / 'probe_acceptance_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
