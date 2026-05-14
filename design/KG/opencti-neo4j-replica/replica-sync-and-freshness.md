# Replica Sync And Freshness

Replica intent:

- The replica is a read-only analysis model beside OpenCTI, not a replacement source of truth.
- Phase one prioritizes a time-window-driven hot subgraph around key entities and `1-2` hop completeness rather than promising a full graph mirror.
- The default bootstrap scope is the last `1` year of changed entities and relationships, with a configurable time window.
- For in-scope changed entities, the replica should complete their `2`-hop neighborhood with a configurable hop depth.

Sync intent:

- Prefer event-driven or live-stream-based sync when OpenCTI can provide it.
- Use live stream as the primary incremental path for new changes entering the replica.
- Use watermark-based incremental pull as a fallback or repair path.
- Reconcile periodically to detect missed updates, missed deletes, and repair drift.

Consistency intent:

- Preserve stable object identity with `standard_id` plus OpenCTI internal IDs for tracking.
- Prefer stable relationship IDs from upstream; otherwise use a composite business key.
- Preserve OpenCTI relationship direction from `source_ref` to `target_ref`.
- Preserve OpenCTI property names in the replica instead of renaming them to local aliases.
- Align deletes, revocations, or tombstones instead of relying on upsert-only behavior.
- Allow replay during recovery, but require idempotent end-state semantics so the replica does not retain duplicates after restart.

Freshness intent:

- Expose freshness and staleness metadata to callers.
- Treat freshness as an explicit contract, not an implicit best effort.

Projection intent:

- The default projection policy is `default baseline + configurable typed extensions` rather than an unrestricted full-property dump.
- The default required field baseline includes `standard_id`, `opencti_id`, `entity_type`, `relationship_type`, `created_at`, `updated_at`, `confidence`, `revoked`, `labels`, `objectMarking`, `name`, and `description`.
- If `name` or `description` exists upstream on an entity or relationship, the replica must preserve the same field name.
- Scalar properties should be preserved as-is, arrays should remain arrays, and nested structures may be minimally flattened or serialized as JSON without semantic renaming.