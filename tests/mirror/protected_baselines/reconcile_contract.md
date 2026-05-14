# Reconcile Contract

1. Physical deletes must remove the corresponding node and attached relationships from the replica.
2. Logical delete, revoke, or invalidate semantics must preserve the object while synchronizing status fields.
3. Reconcile remains responsible for repairing missed deletes, stale status, and drifted relationships.
4. Tests may induce replica-side drift to probe reconcile behavior, but they must not shortcut the repair by importing or invoking mirror-sync internals.