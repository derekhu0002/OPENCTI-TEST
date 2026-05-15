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

endpoint = env.get('OPENCTI_BASE_URL', 'https://localhost').rstrip('/') + '/graphql'
token = env.get('OPENCTI_ADMIN_TOKEN', '')
ctx = ssl._create_unverified_context()
queries = {
    'indicator_search_exact_name': {
        'query': 'query($first: Int!, $search: String) { indicators(first: $first, search: $search, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id name pattern updated_at created_at } } } }',
        'variables': {'first': 20, 'search': 'Mirai-Botnet indicator for 1.2.3.4'},
    },
    'indicator_search_ipv4': {
        'query': 'query($first: Int!, $search: String) { indicators(first: $first, search: $search, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id name pattern updated_at created_at } } } }',
        'variables': {'first': 20, 'search': '1.2.3.4'},
    },
    'malware_search_exact_name': {
        'query': 'query($first: Int!, $search: String) { malwares(first: $first, search: $search, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id name updated_at created_at } } } }',
        'variables': {'first': 20, 'search': 'Mirai-Botnet'},
    },
    'observable_search_ipv4': {
        'query': 'query($first: Int!, $search: String) { stixCyberObservables(first: $first, search: $search, orderBy: updated_at, orderMode: desc) { edges { node { id standard_id entity_type ... on IPv4Addr { value } updated_at created_at } } } }',
        'variables': {'first': 20, 'search': '1.2.3.4'},
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

(root / 'probe_mirai_search.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('probe_mirai_search.json')
