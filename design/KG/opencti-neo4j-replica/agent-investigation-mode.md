# Remote AI Agent Investigation Mode

Intent:

- Support a remote AI Agent acting like an analyst exploring the graph instead of only issuing fixed report queries.
- Preserve OpenCTI as the authoritative source while using the replica for exploration-heavy graph analysis.

Key decisions:

- The Agent may freely explore based on the backend-exposed schema view and query feedback.
- The Agent does not connect directly to Neo4j and does not hold high-privilege database credentials.
- Querying is session-oriented rather than single-call oriented; each investigation should be traceable with an `investigation_id`.

Expected outputs:

- Machine-consumable graph results.
- Human-reviewable investigation material, including evidence nodes, relationships, path context, and freshness metadata.
- Structured feedback for rejected or failed queries so the Agent can self-correct.