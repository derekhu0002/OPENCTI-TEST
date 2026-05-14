# Windowed Sync And Projection Policy

Scope intent:

- The default bootstrap scope is entities and relationships changed within the last `1` year, with the time window configurable.
- The default neighborhood completion depth is `2` hops, with hop depth configurable.
- In-scope changed entities should pull in their in-bound and out-bound neighborhood up to the configured depth while preserving relationship direction.

Phase-one entity scope:

- `Threat-Actor`
- `Malware`
- `Indicator`
- `Campaign`
- `Report`
- `Attack-Pattern`
- `Vulnerability`
- `Infrastructure`
- `Intrusion-Set`
- `Tool`

Projection policy intent:

- Property names in Neo4j should stay aligned with OpenCTI field names.
- The projection mode is `global core baseline + type-specific extensions`.
- Configuration should default to include-based baselines with typed overrides instead of broad blacklist-only filtering.

Required baseline fields:

- `standard_id`
- `opencti_id`
- `entity_type`
- `relationship_type`
- `created_at`
- `updated_at`
- `confidence`
- `revoked`
- `labels`
- `objectMarking`
- `name`
- `description`

Field preservation rules:

- If upstream data contains `name`, the replica must preserve `name`.
- If upstream data contains `description`, the replica must preserve `description`.
- Missing upstream fields must not be fabricated as empty placeholders.

Complex property rules:

- Scalar fields should be preserved as-is.
- Array fields should remain arrays.
- Nested objects may be minimally flattened or serialized as JSON, but semantic field names must not be replaced with local aliases.

Lifecycle rules:

- Physical deletes should remove the corresponding replica node and attached relationships.
- Logical delete, revoke, or invalidate semantics should preserve the object while synchronizing the corresponding status fields.
- Reconcile remains responsible for fixing missed deletes, stale status, and drifted relationships.

Recovery rules:

- Live stream is the preferred incremental ingress path.
- Recovery may replay previously seen events, but the resulting replica state must remain idempotent with no duplicate end-state artifacts.