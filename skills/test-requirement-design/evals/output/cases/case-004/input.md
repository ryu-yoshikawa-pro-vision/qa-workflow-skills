# Evaluation Input

Mode: direct test-requirement design.
Scope: checkout price revalidation before payment authorization.

## Current Effective Authority

- `SPEC-901` (revision `spec-r3`): Before payment authorization, the service recalculates the order total from the latest server-side cart version and current catalog prices. If the cart version differs from the checkout quote, it must reprice before authorization and must never authorize using the stale quoted total.

## Current Product Risk

- `RISK-901`: A stale checkout quote may cause an incorrect customer charge. Current risk level: `高`. The risk owner marks the evidence review as provisional; retain that qualification in the output without changing the supplied level.

## Scope and Instructions

Create test requirements at the integration/API level. Describe verification responsibilities, not concrete test steps or case data. Use the supplied Authority as the only source for expected product behavior. Use the supplied risk only for prioritization; do not turn it into a product rule. Use `assets/output-template.md` in the supplied Skill package.
