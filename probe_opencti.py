import os
import requests
import json

lines = os.environ.get('OPENCTI_VALS', '').split('\n')
url = ''
token = ''
for line in lines:
    if line.startswith('OPENCTI_BASE_URL='):
        url = line.split('=', 1)[1].strip()
    if line.startswith('OPENCTI_ADMIN_TOKEN='):
        token = line.split('=', 1)[1].strip()

if not url: url = "http://localhost:8080" # Default if not found or relative
if url.endswith('/'): url = url[:-1]
if not url.endswith('/graphql'): url += '/graphql'

if not token:
    print('Error: Could not find credentials in .env')
    exit(1)

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def test_query(name, query_body):
    print(f'Testing {name} ordering...')
    payload = {'query': '{ ' + query_body + ' }'}
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f'  {name} ordering FAILED: {data["errors"][0].get("message")}')
            else:
                print(f'  {name} ordering SUCCESS')
        else:
            print(f'  {name} ordering FAILED with status {response.status_code}')
    except Exception as e:
        print(f'  Error testing {name}: {e}')

queries = [
    ('indicators', 'indicators(first: 2, orderBy: updated_at, orderMode: desc) { edges { node { id updated_at } } }'),
    ('malwares', 'malwares(first: 2, orderBy: updated_at, orderMode: desc) { edges { node { id updated_at } } }'),
    ('stixCyberObservables', 'stixCyberObservables(first: 2, orderBy: updated_at, orderMode: desc) { edges { node { id updated_at } } }'),
    ('stixCoreRelationships', 'stixCoreRelationships(first: 2, orderBy: updated_at, orderMode: desc) { edges { node { id updated_at } } }')
]

for name, query_body in queries:
    test_query(name, query_body)

print('\nTesting filter on updated_at for indicators...')
filter_json = {
    'mode': 'and',
    'filters': [{
        'key': 'updated_at',
        'values': ['2020-01-01T00:00:00.000Z'],
        'operator': 'gt'
    }],
    'filterGroups': []
}
query_with_filter = """
query GetIndicators($filters: FilterGroup) {
  indicators(first: 2, filters: $filters) {
    edges {
      node {
        id
        updated_at
      }
    }
  }
}
"""
try:
    response = requests.post(url, headers=headers, json={'query': query_with_filter, 'variables': {'filters': filter_json}}, verify=False)
    if response.status_code == 200:
        data = response.json()
        if 'errors' in data:
            # Try old filter format if FilterGroup fails
            print(f'Filter with FilterGroup FAILED: {data["errors"][0].get("message")}. Trying old format...')
            old_filters = [{ 'key': 'updated_at', 'values': ['2020-01-01T00:00:00.000Z'], 'operator': 'gt' }]
            query_old = 'query GetIndicators($filters: [IndicatorsFiltering]) { indicators(first: 2, filters: $filters) { edges { node { id updated_at } } } }'
            resp_old = requests.post(url, headers=headers, json={'query': query_old, 'variables': {'filters': old_filters}}, verify=False)
            if resp_old.status_code == 200 and 'errors' not in resp_old.json():
                 print('Filter with old format SUCCESS')
            else:
                 print(f'Filter with old format also FAILED')
        else:
            print(f'Filter SUCCESS with FilterGroup')
    else:
        print(f'Filter FAILED with status {response.status_code}')
except Exception as e:
    print(f'Error testing filter: {e}')
