# Bootstrap Window Contract

1. The default bootstrap scope is the last one year of changed entities and relationships unless explicitly overridden.
2. In-scope changed entities must bring in their neighborhood up to the configured default of two hops.
3. Relationship direction must remain aligned with upstream source-to-target semantics.
4. Shared-environment acceptance runs may narrow bootstrap with an explicit start anchor for the current test session, but this does not change the product default one-year rule.