from __future__ import annotations

import json
import ssl
import sys
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent
env = {}
for line in (root / '.env').read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#') or '=' not in line:
        continue
    key, value = line.split('=', 1)
    env[key] = value

since = sys.argv[1]
out_name = sys.argv[2]
endpoint = env.get('OPENCTI_BASE_URL', 'https://localhost').rstrip('/') + '/graphql'
token = env.get('OPENCTI_ADMIN_TOKEN', '')
ctx = ssl._create_unverified_context()
filters = {
    'mode': 'and',
    'filters': [{'key': 'updated_at', 'values': [since], 'operator': 'gt'}],
    'filterGroups': [],
}
queries = {
    'indicators': {
        'query': 'query($first: Int!, $filters: FilterGroup) { indicators(first: $first, filters: $filters, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id name pattern updated_at created_at } } } }',
        'variables': {'first': 20, 'filters': filters},
    },
    'relationships': {
        'query': 'query($first: Int!, $filters: FilterGroup) { stixCoreRelationships(first: $first, filters: $filters, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id relationship_type updated_at created_at from { ... on BasicObject { id standard_id entity_type } } to { ... on BasicObject { id standard_id entity_type } } } } } }',
        'variables': {'first': 20, 'filters': filters},
    },
}
results = {}
for key, payload in queries.items():
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=60, context=ctx) as response:
        results[key] = json.loads(response.read().decode('utf-8'))

(root / out_name).write_text(json.dumps(results, indent=2), encoding='utf-8')
print(out_name)
