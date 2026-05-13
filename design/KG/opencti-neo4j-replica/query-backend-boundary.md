# Query Backend Boundary

Backend role:

- Provide the only execution path from the remote AI Agent to the Neo4j replica.
- Offer graph queries and a controlled Cypher execution entrypoint.

Execution-side responsibility:

- Enforce read-only execution, timeouts, result truncation, execution budgets, auditing, and structured rejection.
- Expose only a backend-approved schema view rather than raw database introspection.
- Avoid silently rewriting Agent Cypher; rejected execution should return structured reasons.

Boundary intent:

- The Agent remains free to explore.
- Safety, resource, and data-boundary controls remain in the backend rather than in prompts or frontend logic.
- If the replica is unavailable or too stale, the backend should return degraded status instead of silently falling back to a non-equivalent GraphQL translation.