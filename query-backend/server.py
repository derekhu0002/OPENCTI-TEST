from __future__ import annotations

import base64
import json
import os
import re
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
FRESHNESS_PATH = ROOT / "mirror-sync" / "runtime" / "freshness.json"
WRITE_PATTERN = re.compile(
    r"\b(create|merge|delete|detach|set|remove|drop|load\s+csv|call\s+dbms|call\s+apoc)\b",
    re.IGNORECASE,
)


def load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def load_freshness() -> dict[str, Any]:
    default_sync_status = os.getenv("QUERY_BACKEND_SYNC_STATUS", "healthy").strip() or "healthy"
    default_staleness = int(os.getenv("QUERY_BACKEND_STALENESS_SECONDS", "0"))
    default_freshness_ts = os.getenv("QUERY_BACKEND_FRESHNESS_TS", "").strip()

    if FRESHNESS_PATH.is_file():
        stored = json.loads(FRESHNESS_PATH.read_text(encoding="utf-8"))
    else:
        stored = {}

    freshness_ts = default_freshness_ts or stored.get("freshness_ts")
    if not freshness_ts:
        freshness_ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    return {
        "backend": "neo4j-replica",
        "freshness_ts": freshness_ts,
        "staleness_seconds": default_staleness if "QUERY_BACKEND_STALENESS_SECONDS" in os.environ else int(stored.get("staleness_seconds", 0)),
        "sync_status": default_sync_status if "QUERY_BACKEND_SYNC_STATUS" in os.environ else stored.get("sync_status", default_sync_status),
    }


def is_readonly_cypher(cypher: str) -> bool:
    return WRITE_PATTERN.search(cypher or "") is None


def neo4j_endpoint(env_values: dict[str, str]) -> str:
    host = os.getenv("NEO4J_MIRROR_HTTP_HOST", env_values.get("NEO4J_ADVERTISED_HOST", "localhost"))
    port = os.getenv("NEO4J_MIRROR_HTTP_PORT", env_values.get("NEO4J_HTTP_PORT", "7474"))
    return f"http://{host}:{port}/db/neo4j/tx/commit"


def neo4j_headers(env_values: dict[str, str]) -> dict[str, str]:
    username = os.getenv("NEO4J_MIRROR_USERNAME", "neo4j")
    password = os.getenv("NEO4J_MIRROR_PASSWORD", env_values.get("NEO4J_PASSWORD", ""))
    if not password:
        raise AssertionError("Missing Neo4j mirror password")
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def execute_query(cypher: str, limit: int = 100) -> tuple[list[dict[str, Any]], bool]:
    env_values = load_env_file()
    statement = cypher.strip()
    if " limit " not in statement.lower():
        statement = f"{statement} LIMIT {limit}"

    payload = json.dumps(
        {
            "statements": [
                {
                    "statement": statement,
                    "resultDataContents": ["row"],
                }
            ]
        }
    ).encode("utf-8")
    http_request = request.Request(
        neo4j_endpoint(env_values),
        data=payload,
        headers=neo4j_headers(env_values),
        method="POST",
    )
    with request.urlopen(http_request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    errors = body.get("errors", [])
    if errors:
        raise AssertionError(f"Neo4j query failed: {errors}")
    result = body.get("results", [{}])[0]
    columns = result.get("columns", [])
    rows: list[dict[str, Any]] = []
    for item in result.get("data", []):
        row = item.get("row", [])
        rows.append(dict(zip(columns, row, strict=False)))
    return rows, False


def build_rejection(payload: dict[str, Any], rejection_reason: str) -> dict[str, Any]:
    return {
        "backend": "neo4j-replica",
        "investigation_id": payload.get("investigation_id"),
        "rejection_reason": rejection_reason,
        "budget_policy": "readonly-default",
    }


def build_degraded(payload: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "backend": "neo4j-replica",
        "investigation_id": payload.get("investigation_id"),
        "freshness_ts": freshness["freshness_ts"],
        "staleness_seconds": freshness["staleness_seconds"],
        "sync_status": freshness["sync_status"],
    }


def audit_event(event: dict[str, Any]) -> None:
    audit_path = Path(os.getenv("QUERY_BACKEND_AUDIT_LOG", ROOT / "query-backend" / "runtime" / "audit.log"))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")


class QueryBackendHandler(BaseHTTPRequestHandler):
    server_version = "OpenCTIQueryBackend/1.0"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/graph/query":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        investigation_id = str(payload.get("investigation_id", "")).strip()
        cypher = str(payload.get("cypher", "")).strip()
        if not investigation_id or not cypher:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "missing_investigation_or_cypher"})
            return

        freshness = load_freshness()
        audit_base = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "investigation_id": investigation_id,
            "cypher": cypher,
            "sync_status": freshness["sync_status"],
        }

        if not is_readonly_cypher(cypher):
            response_body = build_rejection(payload, "write_operation_not_allowed")
            audit_event({**audit_base, "decision": "rejected", "rejection_reason": response_body["rejection_reason"]})
            self._write_json(HTTPStatus.BAD_REQUEST, response_body)
            return

        if freshness["sync_status"] != "healthy":
            response_body = build_degraded(payload, freshness)
            audit_event({**audit_base, "decision": "degraded"})
            self._write_json(HTTPStatus.OK, response_body)
            return

        try:
            results, result_truncated = execute_query(cypher)
        except (AssertionError, error.URLError) as exc:
            response_body = {
                **build_degraded(payload, {**freshness, "sync_status": "unavailable"}),
                "error": str(exc),
            }
            audit_event({**audit_base, "decision": "degraded", "error": str(exc)})
            self._write_json(HTTPStatus.OK, response_body)
            return

        response_body = {
            "backend": "neo4j-replica",
            "investigation_id": investigation_id,
            "freshness_ts": freshness["freshness_ts"],
            "staleness_seconds": freshness["staleness_seconds"],
            "sync_status": freshness["sync_status"],
            "results": results,
            "result_truncated": result_truncated,
        }
        audit_event({**audit_base, "decision": "executed", "result_count": len(results)})
        self._write_json(HTTPStatus.OK, response_body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _write_json(self, status: HTTPStatus, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def serve() -> None:
    port = int(os.getenv("QUERY_BACKEND_PORT", "8088"))
    host = os.getenv("QUERY_BACKEND_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), QueryBackendHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()