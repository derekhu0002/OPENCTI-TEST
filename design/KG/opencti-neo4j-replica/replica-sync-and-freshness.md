# Replica Sync And Freshness

Replica intent:

- The replica is a read-only analysis model beside OpenCTI, not a replacement source of truth.
- Phase one prioritizes a hot subgraph around key entities and `1-2` hop completeness rather than promising a full graph mirror.

Sync intent:

- Prefer event-driven or live-stream-based sync when OpenCTI can provide it.
- Use watermark-based incremental pull as a fallback or repair path.
- Reconcile periodically to detect missed updates and repair drift.

Consistency intent:

- Preserve stable object identity with `standard_id` plus OpenCTI internal IDs for tracking.
- Prefer stable relationship IDs from upstream; otherwise use a composite business key.
- Align deletes, revocations, or tombstones instead of relying on upsert-only behavior.

Freshness intent:

- Expose freshness and staleness metadata to callers.
- Treat freshness as an explicit contract, not an implicit best effort.