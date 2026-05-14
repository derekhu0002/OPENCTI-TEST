# Reconcile Probe

Scenario fixture for the frozen mirror acceptance entry covering delete alignment, revoke alignment, and reconcile repair.

Expected setup facts:

1. The replica already contains synchronized objects and relationships.
2. Upstream can produce a physical delete or a revoke-style status change.
3. Reconcile can run after incremental sync to repair drift.
4. The test may create drift inside the replica itself to verify reconcile repair, but it must not call mirror-sync internals to fake a successful repair.