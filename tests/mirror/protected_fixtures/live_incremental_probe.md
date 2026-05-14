# Live Incremental Probe

Scenario fixture for the frozen mirror acceptance entries covering live-stream incremental sync and watermark-based recovery.

Expected setup facts:

1. Live stream ingestion is enabled for the mirror sync flow.
2. The mirror tracks a durable watermark for restart recovery.
3. A new change can be emitted after bootstrap without requiring full reseed.
4. The test stimulus is an upstream OpenCTI mutation created after the current bootstrap anchor.
5. The acceptance path waits for the real replica to observe the change instead of invoking the sync implementation directly.