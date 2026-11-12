---
name: test-condition-analysis
description: Independently identify reusable common test-condition candidates from current specifications, Authority refs, product feature inventory, and available UI or item refs. Use for stable COND IDs, evidence, lifecycle, source revision impact, and advisory candidate crosschecks; do not use for formal TCN/CI, item applicability decisions, expected results, risk scoring, or test execution.
---

# Test Condition Analysis

Identify common test-condition candidates independently of test-item analysis. Conditions may be identified before item candidates are final and may be shared across features or item kinds. They remain candidates until `test-condition-design` determines formal applicability, disposition, TCN, CI, and expected-result candidates.

## Start when

- A user asks to identify or maintain reusable common condition candidates from current sources.
- A changed Authority, source, or known item set requires condition impact analysis.
- Item and condition candidate artifacts are ready for advisory crosscheck.

Do not start for formal TCN / CI / disposition / expected-result design (`test-condition-design`), Product Risk (`test-analysis`), Authority or expected behavior (`spec-analysis`), test items alone (`test-item-analysis`), concrete test cases, or execution.

## Required work

1. Read the exact B snapshot and its separate `feature_registry.analyze()` report as `{ "snapshot": ..., "analysis": ... }`, plus current Authority/source refs. Preserve project/artifact refs, artifact and source revisions, snapshot hash, source inventory, feature IDs, and unknown areas. An `incomplete` report remains incomplete; reject `stale`, `blocked`, `idempotent`, mismatched, or malformed results. Do not replace B's validator.
2. Identify candidates across input constraints, boundaries, authorization, business states, transitions, recovery, external dependencies, data integrity, and nonfunctional concerns. A general checklist helps discovery but is not source evidence or an expected result.
3. Record stable `COND-*` IDs, intent, candidate kind, applicable item kinds, feature/known item refs, Authority entity refs, source refs/revisions, candidate state, unknowns, history, and currentness.
4. Reuse an existing ID only for the same meaning. Same-name candidates with different meaning keep separate IDs. A split or merge creates new IDs and history; retirement is explicit and never permits ID reuse.
5. Use `scripts/condition_candidates.py` for deterministic identity allocation, history, source impact, and non-formal crosscheck. `no_change` means only that candidate content is unchanged; report the separate analysis state, issues, unresolved condition IDs, and recheck targets. `valid` is structural validity only. The crosscheck considers only supplied candidate pairs; it never expands the full item × condition Cartesian product.
6. Report possible missing item refs, item candidates without a pair proposal, condition candidates without a pair proposal, incomplete source population, and unconfirmed candidates as review prompts. Do not decide applicability, exclusion, duplication, or coverage.
7. Keep candidate counts, E-owned applicability/formal-design results, and execution counts separate. D outputs `null`/not-provided for measurements owned by E or execution owners; zero candidates do not mean 100% coverage.

Older v1 item and condition artifacts without `feature_inventory_context` remain readable with IDs/history preserved, but their crosscheck is incomplete until a new materialization carries current B context. A well-formed item ID that is not present is reported as unconfirmed with a recheck request; D does not create the item or decide that it is formally rejected.

## Save and resume

The artifact owner is `test-condition-analysis`; `artifact_ref` is a logical owner ref, not a file path. A write precondition carries owner, scope, artifact ref, expected provider revision, source refs/revisions, permission requirement, approval ref, and resume owner for the A-owned adapter. The helper does not persist data or authenticate permission/approval. The selected provider must perform native CAS/create-if-absent and an independent hash-matching readback before the artifact is current. Preserve draft output and block persistence if that contract is unavailable. Re-evaluate only candidates affected by changed evidence refs.

Use `assets/output-template.md` and the contracts in `references/guidance.md` and `references/data-contract.md`.
