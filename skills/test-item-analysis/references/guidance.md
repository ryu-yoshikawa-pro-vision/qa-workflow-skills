# Test item analysis guidance

## Owner boundary

`test-item-analysis` owns only test-item candidate identity, hierarchy, feature links, implementation state, evidence refs, revision history, and local change impact. `feature-analysis` owns product feature inventory. `spec-analysis` owns expected behavior and Authority. `ui-target-analysis` owns UI structures and interactions. `test-analysis` owns Product Risk and test focus. `test-requirement-design` owns TR. `test-condition-analysis` owns common condition candidates. `test-condition-design` owns formal TCN, applicability/disposition, CI and expected-result candidates. `test-case-design` owns concrete test cases.

The skill may report a possible missing item or source gap. It cannot certify that every product feature was found, convert an observation into expected behavior, adopt a condition for an item, or assert formal coverage.

## Identity and history

- IDs use `ITEM-001`, `ITEM-002`, … and are allocated from the full retained `id_history` by `scripts/item_candidates.py`. A caller cannot supply a new stable ID.
- `candidate_key` and `@draft:<key>` are request-local references only. They are not persisted identities.
- `reuse` must cite one active item in the current artifact. `split` and `merge` allocate new IDs and cite existing source IDs plus a reason. A merge does not retire its source IDs automatically.
- `retirements[]` explicitly names an active ID, reason, and current evidence. A retired ID remains in `id_history` and cannot be reused.
- Names and descriptions may change under the same item ID only with an explicit reuse decision and reason. Equal names do not trigger a merge; semantic deduplication remains an owner judgment.
- Parent references resolve to an existing stable ID or a request-local `@draft:<candidate_key>`. The final parent graph must be acyclic.

## Source and impact

Read B's `feature-inventory-v1` owner output, including `artifact_revision`, `source_revision`, and `handoff.snapshot_sha256`. The D helper checks the published structure and carries the source identity forward; B's validator remains responsible for validating the inventory itself.

Each item cites one or more current source refs with `owner`, `scope`, `artifact_ref`, `revision`, and lowercase SHA-256 `content_hash`. `impact` compares the item's evidence refs against currently supplied source refs. A changed source marks only linked items stale; a missing source marks them unknown. Keep old refs in history and do not silently refresh evidence.

## Candidate coverage

The only measurable D-owned rate is confirmed active feature candidates represented by non-retired items divided by the same complete active feature population. A partial, stale, or empty population yields a null rate. This is candidate identification over the confirmed inventory, not product-wide discovery, item-condition applicability, formal design coverage, or execution coverage.
