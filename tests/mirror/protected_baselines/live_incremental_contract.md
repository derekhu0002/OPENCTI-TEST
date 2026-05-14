# Live Incremental Contract

1. New upstream changes must reach the replica through the incremental path without requiring a full manual reseed.
2. Watermark-based recovery may replay previously seen events, but the resulting replica state must remain idempotent.
3. Freshness metadata must remain part of the replica contract after incremental updates.
4. Incremental acceptance must be driven by real upstream writes performed after the current test anchor, not by direct test-side calls into mirror-sync.