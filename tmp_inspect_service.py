from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path.cwd()
SERVICE_PATH = ROOT / 'mirror-sync' / 'service.py'
SPEC = importlib.util.spec_from_file_location('mirror_sync_service', SERVICE_PATH)
assert SPEC is not None and SPEC.loader is not None
service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(service)

state = service._load_watermark_state()
since = service._effective_since(state)
recent_indicators = service._fetch_recent_indicators(since)
recent_relationships = service._fetch_recent_relationships(since)
named_indicators = service._fetch_named_replica_indicators(since)

payload = {
    'since': since.astimezone(service.UTC).isoformat().replace('+00:00', 'Z'),
    'state_bootstrap_start_at': state.get('bootstrap_start_at'),
    'state_last_synced_at': state.get('last_synced_at'),
    'recent_indicator_names': [item.get('name') for item in recent_indicators],
    'recent_relationship_types': [item.get('relationship_type') for item in recent_relationships],
    'named_indicator_names': [item.get('name') for item in named_indicators],
}

if named_indicators:
    indicator_name = str(named_indicators[0].get('name', ''))
    if ' indicator for ' in indicator_name:
        malware_name, ipv4_value = indicator_name.rsplit(' indicator for ', 1)
        payload['first_named_indicator'] = indicator_name
        payload['observable_lookup'] = service._fetch_observable_by_value(ipv4_value)
        payload['malware_lookup'] = service._fetch_malware_by_name(malware_name)

(ROOT / 'service_inspect.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
