# Projection Policy Contract

1. Replica property names must stay aligned with OpenCTI field names instead of local aliases.
2. The default projection baseline must preserve the required fields declared by the intent architecture.
3. If upstream data contains `name` or `description`, the replica must preserve the same field names.
4. Projection-policy acceptance remains valid only when the inspected replica state was produced by the real sync path.