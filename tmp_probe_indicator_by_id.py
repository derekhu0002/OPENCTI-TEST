from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent
env = {}
for line in (root / '.env').read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    env[key] = value

indicator_id = '2242e064-e597-4de5-ac4f-cadf032467c9'
endpoint = env.get('OPENCTI_BASE_URL', 'https://localhost').rstrip('/') + '/graphql'
token = env.get('OPENCTI_ADMIN_TOKEN', '')
ctx = ssl._create_unverified_context()

queries = {
    'search_indicators_by_id': {
        'query': 'query($first: Int!, $search: String) { indicators(first: $first, search: $search, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id name pattern updated_at created_at } } } }',
        'variables': {'first': 10, 'search': indicator_id},
    },
    'indicator_by_id': {
        'query': 'query($id: String!) { indicator(id: $id) { id standard_id name pattern updated_at created_at } }',
        'variables': {'id': indicator_id},
    },
    'stix_domain_object_by_id': {
        'query': 'query($id: String!) { stixDomainObject(id: $id) { id entity_type ... on Indicator { standard_id name pattern updated_at created_at } } }',
        'variables': {'id': indicator_id},
    },
}

results = {}
for name, payload in queries.items():
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=60, context=ctx) as response:
        results[name] = json.loads(response.read().decode('utf-8'))

(root / 'probe_indicator_by_id.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('wrote probe_indicator_by_id.json')
