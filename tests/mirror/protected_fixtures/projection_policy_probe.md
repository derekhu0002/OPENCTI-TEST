# Projection Policy Probe

Scenario fixture for the frozen mirror acceptance entry covering property-name preservation and the default projection baseline.

Expected setup facts:

1. Upstream entities or relationships expose default baseline fields.
2. At least one synchronized object includes `name` or `description`.
3. The replica projection policy uses aligned OpenCTI field names.
4. The synchronized sample must arrive through the real mirror pipeline after GraphQL seeding, not through a direct test-side projection helper.