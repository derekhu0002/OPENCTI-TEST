import json, ssl, urllib.request
from pathlib import Path
root = Path(r'd:\Projects\OPENCTI-TEST')
env = {}
for line in (root / '.env').read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    env[k] = v
url = env.get('OPENCTI_BASE_URL', 'https://localhost').rstrip('/') + '/graphql'
token = env.get('OPENCTI_ADMIN_TOKEN', '')
ctx = ssl._create_unverified_context()
queries = {
    'observables': 'query { stixCyberObservables(first: 5, orderBy: updated_at, orderMode: desc) { edges { node { standard_id updated_at created_at ... on IPv4Addr { value } } } } }',
    'indicators': 'query { indicators(first: 5, orderBy: updated_at, orderMode: desc) { edges { node { standard_id name updated_at created_at } } } }',
    'malwares': 'query { malwares(first: 5, orderBy: updated_at, orderMode: desc) { edges { node { standard_id name updated_at created_at } } } }',
    'relationships': 'query { stixCoreRelationships(first: 5, orderBy: updated_at, orderMode: desc) { edges { node { relationship_type updated_at created_at from { ... on BasicObject { standard_id entity_type } } to { ... on BasicObject { standard_id entity_type } } } } } }',
}
for name, query in queries.items():
    req = urllib.request.Request(url, data=json.dumps({'query': query}).encode('utf-8'), headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    print(name)
    print(json.dumps(body, indent=2)[:2000])
    print('---')
