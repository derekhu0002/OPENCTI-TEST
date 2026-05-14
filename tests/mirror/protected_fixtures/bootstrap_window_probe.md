# Bootstrap Window Probe

Scenario fixture for the frozen mirror acceptance entries covering the default one-year bootstrap window and two-hop neighborhood completion.

Expected setup facts:

1. OpenCTI contains at least one key entity changed within the default one-year window.
2. The changed entity has both inbound and outbound relationships within two hops.
3. The sync scope uses the default bootstrap window unless explicitly overridden.
4. In shared real environments, the test fixture may record a bootstrap start anchor so the sync service only scans a narrow window around the current test run.
5. The scenario must be established through real OpenCTI writes; the test must not import or call mirror-sync internals to force replica writes.