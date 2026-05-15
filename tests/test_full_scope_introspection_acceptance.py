from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
FULL_SCOPE_INTROSPECTION_PATH = ROOT / "mirror-sync" / "runtime" / "full_scope_introspection.json"


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _opencti_graphql_endpoint(env_values: dict[str, str]) -> str:
    base_url = os.getenv("OPENCTI_URL", env_values.get("OPENCTI_BASE_URL", "https://localhost")).rstrip("/")
    return f"{base_url}/graphql"


def _opencti_graphql_headers(env_values: dict[str, str]) -> dict[str, str]:
    token = os.getenv("OPENCTI_TOKEN", env_values.get("OPENCTI_ADMIN_TOKEN", "")).strip()
    if not token:
        raise AssertionError("Missing OpenCTI token for full-scope introspection acceptance")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _graphql_request(query: str, variables: dict[str, object] | None = None) -> dict[str, object]:
    env_values = _load_env_file()
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    endpoint = _opencti_graphql_endpoint(env_values)
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers=_opencti_graphql_headers(env_values),
        method="POST",
    )
    ssl_context = ssl._create_unverified_context() if endpoint.startswith("https://") else None
    try:
        with urllib.request.urlopen(request, timeout=120, context=ssl_context) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise AssertionError(f"OpenCTI GraphQL introspection request failed: {exc}") from exc
    errors = body.get("errors")
    if errors:
        raise AssertionError(f"OpenCTI GraphQL introspection returned errors: {errors}")
    return body["data"]


def _full_introspection_query() -> str:
    return """
query FullIntrospection {
  __schema {
    queryType { ...FullTypeRef }
    mutationType { ...FullTypeRef }
    subscriptionType { ...FullTypeRef }
    types {
      kind
      name
      fields(includeDeprecated: true) {
        name
        args {
          name
          type { ...FullTypeRef }
        }
        type { ...FullTypeRef }
      }
      inputFields {
        name
        type { ...FullTypeRef }
      }
      interfaces { ...FullTypeRef }
      enumValues(includeDeprecated: true) {
        name
      }
      possibleTypes { ...FullTypeRef }
    }
    directives {
      name
      args {
        name
        type { ...FullTypeRef }
      }
    }
  }
}

fragment FullTypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
    }
  }
}
"""


def _load_snapshot_schema() -> dict[str, object]:
    payload = json.loads(FULL_SCOPE_INTROSPECTION_PATH.read_text(encoding="utf-8"))
    return dict(payload["data"]["__schema"])


def _load_live_schema() -> dict[str, object]:
    return dict(_graphql_request(_full_introspection_query())["__schema"])


def _named_type_ref(type_ref: dict[str, object] | None) -> tuple[str | None, str | None]:
    current = type_ref
    while isinstance(current, dict):
        name = current.get("name")
        kind = current.get("kind")
        if name:
            return str(kind) if kind is not None else None, str(name)
        next_type = current.get("ofType")
        if not isinstance(next_type, dict):
            return str(kind) if kind is not None else None, None
        current = next_type
    return None, None


def _iter_named_types(schema: dict[str, object]) -> list[dict[str, object]]:
    return [
        item
        for item in schema.get("types", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip() and not str(item.get("name", "")).startswith("__")
    ]


def _schema_elements(schema: dict[str, object]) -> set[str]:
    elements = {str(item["name"]) for item in _iter_named_types(schema)}
    for directive in schema.get("directives", []):
        if isinstance(directive, dict) and directive.get("name"):
            elements.add(f"directive:{directive['name']}")
    for root_key in ("queryType", "mutationType", "subscriptionType"):
        root_type = schema.get(root_key)
        if isinstance(root_type, dict) and root_type.get("name"):
            elements.add(f"root:{root_key}:{root_type['name']}")
    return elements


def _schema_relationships(schema: dict[str, object]) -> set[str]:
    relationships: set[str] = set()
    for type_payload in _iter_named_types(schema):
        type_name = str(type_payload["name"])
        for interface in type_payload.get("interfaces") or []:
            _, interface_name = _named_type_ref(interface)
            if interface_name:
                relationships.add(f"implements:{type_name}->{interface_name}")
        for possible_type in type_payload.get("possibleTypes") or []:
            _, possible_type_name = _named_type_ref(possible_type)
            if possible_type_name:
                relationships.add(f"possible:{type_name}->{possible_type_name}")
        for field in type_payload.get("fields") or []:
            if not isinstance(field, dict) or not field.get("name"):
                continue
            target_kind, target_name = _named_type_ref(field.get("type"))
            if target_kind in {"OBJECT", "INTERFACE", "UNION"} and target_name:
                relationships.add(f"field:{type_name}.{field['name']}->{target_name}")
    return relationships


def _schema_properties(schema: dict[str, object]) -> set[str]:
    properties: set[str] = set()
    for type_payload in _iter_named_types(schema):
        type_name = str(type_payload["name"])
        for field in type_payload.get("fields") or []:
            if not isinstance(field, dict) or not field.get("name"):
                continue
            properties.add(f"field:{type_name}.{field['name']}")
            for arg in field.get("args") or []:
                if isinstance(arg, dict) and arg.get("name"):
                    properties.add(f"arg:{type_name}.{field['name']}({arg['name']})")
        for input_field in type_payload.get("inputFields") or []:
            if isinstance(input_field, dict) and input_field.get("name"):
                properties.add(f"input:{type_name}.{input_field['name']}")
        for enum_value in type_payload.get("enumValues") or []:
            if isinstance(enum_value, dict) and enum_value.get("name"):
                properties.add(f"enum:{type_name}.{enum_value['name']}")
    for directive in schema.get("directives", []):
        if not isinstance(directive, dict) or not directive.get("name"):
            continue
        directive_name = str(directive["name"])
        properties.add(f"directive:{directive_name}")
        for arg in directive.get("args") or []:
            if isinstance(arg, dict) and arg.get("name"):
                properties.add(f"directive-arg:{directive_name}({arg['name']})")
    return properties


def _missing_examples(snapshot_items: set[str], live_items: set[str]) -> str:
    missing = sorted(live_items - snapshot_items)
    return ", ".join(missing[:10])


def test_full_scope_introspection_covers_live_opencti_schema() -> None:
    assert FULL_SCOPE_INTROSPECTION_PATH.is_file(), "Missing full scope introspection snapshot"

    snapshot_schema = _load_snapshot_schema()
    live_schema = _load_live_schema()

    snapshot_elements = _schema_elements(snapshot_schema)
    live_elements = _schema_elements(live_schema)
    assert live_elements <= snapshot_elements, (
        "full_scope_introspection.json is missing live schema elements; examples: "
        f"{_missing_examples(snapshot_elements, live_elements)}"
    )

    snapshot_relationships = _schema_relationships(snapshot_schema)
    live_relationships = _schema_relationships(live_schema)
    assert live_relationships <= snapshot_relationships, (
        "full_scope_introspection.json is missing live schema relationships; examples: "
        f"{_missing_examples(snapshot_relationships, live_relationships)}"
    )

    snapshot_properties = _schema_properties(snapshot_schema)
    live_properties = _schema_properties(live_schema)
    assert live_properties <= snapshot_properties, (
        "full_scope_introspection.json is missing live schema properties; examples: "
        f"{_missing_examples(snapshot_properties, live_properties)}"
    )