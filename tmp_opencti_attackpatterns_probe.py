import json, ssl, urllib.request
base_url = "https://localhost"
token = r"""c118a69a-9d60-441f-b30b-a0967694707e"""
query = """
query MirrorProbe {
  attackPatterns(first: 5, orderBy: updated_at, orderMode: desc) {
    edges { node { id standard_id name updated_at created_at entity_type } }
    pageInfo { hasNextPage endCursor }
  }
  malwares(first: 5, orderBy: updated_at, orderMode: desc) {
    edges { node { id standard_id name updated_at created_at entity_type } }
    pageInfo { hasNextPage endCursor }
  }
}
"""
req = urllib.request.Request(
    base_url.rstrip('/') + '/graphql',
    data=json.dumps({'query': query, 'variables': {}}).encode('utf-8'),
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    method='POST',
)
ctx = ssl._create_unverified_context()
with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
    body = json.loads(response.read().decode('utf-8'))
print(json.dumps(body, indent=2))
