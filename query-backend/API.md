# Query Backend API

## Purpose

This document defines the external query-backend interface that fronts the Neo4j replica for remote investigation flows.

## Endpoint

- Method: `POST`
- Path: `/graph/query`
- Content-Type: `application/json`
- Authentication: optional `Authorization: Bearer <token>` when the deployment requires it

## Request

Required fields:

- `investigation_id`: stable session identifier used for audit correlation
- `cypher`: backend-reviewed read-only Cypher to execute against the replica

Example:

```json
{
  "investigation_id": "case-2026-05-13-001",
  "cypher": "MATCH (n) RETURN n LIMIT 1"
}
```

## Success Response

Fields:

- `backend`: always `neo4j-replica`
- `investigation_id`: echoed from the request
- `freshness_ts`: last known replica freshness timestamp
- `staleness_seconds`: replica age in seconds
- `sync_status`: replica health state
- `results`: machine-consumable result rows
- `result_truncated`: whether backend-side truncation was applied

Example:

```json
{
  "backend": "neo4j-replica",
  "investigation_id": "case-2026-05-13-001",
  "freshness_ts": "2026-05-13T08:00:00Z",
  "staleness_seconds": 0,
  "sync_status": "healthy",
  "results": [
    {
      "value": "1.2.3.4",
      "standard_id": "ipv4-addr--7dd44d27-f473-5ba9-b12b-0d3a61bbed2e"
    }
  ],
  "result_truncated": false
}
```

## Rejection Response

Returned when the backend rejects a query before execution.

Fields:

- `backend`
- `investigation_id`
- `rejection_reason`
- `budget_policy`

Example:

```json
{
  "backend": "neo4j-replica",
  "investigation_id": "case-2026-05-13-001",
  "rejection_reason": "write_operation_not_allowed",
  "budget_policy": "readonly-default"
}
```

## Degraded Response

Returned when the replica cannot be used safely.

Fields:

- `backend`
- `investigation_id`
- `freshness_ts`
- `staleness_seconds`
- `sync_status`

Example:

```json
{
  "backend": "neo4j-replica",
  "investigation_id": "case-2026-05-13-001",
  "freshness_ts": "2026-05-13T07:52:00Z",
  "staleness_seconds": 960,
  "sync_status": "stale"
}
```

## Constraints

- The backend executes only against the Neo4j replica.
- The backend does not silently fall back to OpenCTI GraphQL translation.
- Write-oriented Cypher is rejected before execution.
- Every request is audit logged with `investigation_id`, Cypher, and backend decision.