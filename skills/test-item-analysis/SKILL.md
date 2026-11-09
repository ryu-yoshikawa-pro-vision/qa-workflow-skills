---
name: test-item-analysis
description: Identify and maintain stable test-item candidates for product features, screens, APIs, batches, components, events, and data flows, including hierarchy, many-to-many feature references, status, source evidence, history, and change impact. Use for test targets and item identity; do not use to inventory product features, decide specifications or risks, create formal test requirements or conditions, or execute tests.
---

# Test Item Analysis

Manage test items as a separate, stable inventory. A test item is a product element to be tested; it is not a product feature, UI structure, specification, risk, test requirement, formal test condition, coverage item, test case, or execution result.

## Start when

- A user asks to identify, create, update, split, merge, retire, or trace test items.
- A current product feature inventory or authorized specification/UI source needs candidate test items.
- A source revision changed and the affected item candidates need impact analysis.

Do not start for product feature discovery alone (`feature-analysis`), UI structure alone (`ui-target-analysis`), expected behavior or Authority (`spec-analysis`), Product Risk (`test-analysis`), TR (`test-requirement-design`), formal item-specific TCN/Disposition/CI (`test-condition-design`), concrete test cases (`test-case-design`), or test execution.

## Required work

1. Read the exact B snapshot and its separate `feature_registry.analyze()` report as `{ "snapshot": ..., "analysis": ... }`. Preserve project/artifact refs, artifact and source revisions, snapshot hash, source inventory, feature IDs, and unknown areas. Accept `incomplete` only as incomplete input; reject `stale`, `blocked`, `idempotent`, mismatched, or malformed results. Do not replace B's validator.
2. Read the prior `test-item-candidates-v1` artifact and its provider revision when one exists. Never use a path, name, test level, or display title as an item ID.
3. Identify candidate items from their evidence. Keep UI, API, batch, component, event, integration, data, security, and nonfunctional targets in scope where supported. Reuse one stable item ID across test levels.
4. Decide identity from meaning and evidence. Reuse an active ID only when the candidate is the same item. A split or merge creates new IDs with explicit relation history; retire old IDs only through an explicit retirement with evidence. Names are not identity: same-name items may remain separate, and differently named items are not silently merged.
5. Retain parent/child references, multiple feature references, implementation status (`planned`, `unimplemented`, `implemented`, `unknown`), source evidence, and append-only history. Reject missing references and parent cycles.
6. Use `scripts/item_candidates.py` for deterministic allocation and contract checks. The helper creates only a candidate payload and precondition; it does not write an artifact or prove provider CAS, authorization, approval, or readback.
7. Report uncovered known feature candidates and source uncertainty separately. Only calculate feature-to-item candidate identification over a complete, nonempty, current feature inventory. Do not turn unknown scope, stale items, or a zero denominator into 100%.
8. Hand `ITEM-*` refs, candidate revision fingerprint, source refs/revisions, validator evidence, gaps, and unknowns to `test-condition-analysis` and `test-condition-design`. Candidate correspondence is advisory; do not decide item-condition applicability, formal coverage, expected results, or execution.

Older v1 artifacts without `feature_inventory_context` remain readable and retain their IDs/history. They cannot establish a complete source population in crosscheck; the next successful materialization adds current B context without rewriting prior events.

## Save and resume

The artifact owner is `test-item-analysis`; `artifact_ref` is a logical owner reference, not a file path. The write precondition includes owner, scope, artifact ref, expected provider revision, source refs/revisions, permission requirement, approval ref, and resume owner for the A-owned adapter. No save is complete until the selected provider performs native create-if-absent or revision CAS and an independent readback matches the content hash. Preserve the candidate and block persistence if the provider, approval policy, expected revision, or readback is unavailable. Reopen using the same source refs and provider revision; revalidate only impacted items.

Use the output format in `assets/output-template.md` and detailed contracts in `references/guidance.md` and `references/data-contract.md`.
