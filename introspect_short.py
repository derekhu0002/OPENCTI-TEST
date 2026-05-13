import requests
import json
import os

def load_env():
    env = {}
    if os.path.exists('.env'):
        with open('.env', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    parts = line.strip().split('=', 1)
                    if len(parts) == 2:
                        env[parts[0]] = parts[1].strip('\"').strip(\"'\")
    return env

env = load_env()
url = env.get('OPENCTI_URL', 'http://localhost:4000/graphql')
if not url.endswith('/graphql'):
    url += '/graphql'
token = env.get('OPENCTI_TOKEN', '')

query = \"\"\"
query IntrospectionQuery {
  __type(name: \"Mutation\") {
    fields {
      name
      args {
        name
        type {
          name
          kind
          ofType {
            name
            kind
            ofType {
              name
              kind
            }
          }
        }
      }
    }
  }
}
\"\"\"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

try:
    response = requests.post(url, json={'query': query}, headers=headers, timeout=10)
    data = response.json()
    mutation_fields = data.get('data', {}).get('__type', {}).get('fields', [])
    found = False
    for field in mutation_fields:
        if field['name'] == 'stixCyberObservableAdd':
            found = True
            for arg in field['args']:
                print(f\"{arg['name']}: {arg['type']['name'] or arg['type']['kind']}\")
    if not found:
        print(\"Field stixCyberObservableAdd not found in Mutation\")
except Exception as e:
    print(f\"Error: {e}\")