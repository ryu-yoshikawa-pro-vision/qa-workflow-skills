# PR #11 Partial Rerun Projection and Runtime Scope Follow-up

## Starting state

- Local branch: `feat/deterministic-test-technique-automation`
- Local HEAD: `cc68139025f9f8ccb67b188accf515f5ef099e9b`
- PR #11 head: `cc68139025f9f8ccb67b188accf515f5ef099e9b`
- PR state at start: open, ready for review, mergeable
- Worktree at start: clean

## Changes

- `verify_runtime_evidence()` now checks the normalized previous full ID state and update scopes before deciding whether a previous artifact is required. It rejects a null previous artifact when an active scope-out TR, TCN, model, CI, or TC must be preserved; it does not require one when all previous active core IDs are inside the update scope.
- Expected entity identities remain derived from normalized input, fixed runtime results, validated previous state, ownership, and the `update_scope_*` boundary. They are never inferred from candidate `Machine Entities`.
- A valid standalone verification result now exposes its fixed `current_structure_state` projection, including strict, canonical `carry_forward_entities[]` rows. `workflow_runtime.py` and `traceability.py` consume that projection through the same `_expected_entities()` helper and reject a missing projection when scope-out active IDs require it. The projection preserves row content, fingerprints, and dependencies.
- Previous `ci_id_state[]` is read from each production-shaped `artifact:materialize_coverage:<TCN ID>` result and merged by TCN. The validator checks each CI prefix, rejects duplicate CI identities and duplicate/non-owner state sources, and compares normalized `previous_ci_ids[]` only to the current TCN subset. Materialize input rejects a CI ID owned by another TCN.
- The runtime Plan now documents the entity-scoped runtime dependency key, its digest and generation inputs, its base-runtime resolution, and its exclusion from dispatch/runtime-unit graphs. Partial-rerun Plan text documents the same carry-forward and freshness boundary.

## Regression tests

- Added standalone tests for null previous artifact rejection with scope-out TR, TCN/model, and TC state, and for allowing null when no carry-forward is needed.
- Added a production-shaped previous test-condition-design artifact with one `condition_structure:all` state and separate TCN-scoped materialize results. Tests cover order-independent CI state merging, scope-out TCN/model/CI/TDR/Disposition carry-forward, bad CI prefix, duplicate CI identity, cross-TCN normalized CI state, and status mismatch.
- Added workflow and traceability tests for fixed carry-forward projections containing scope-out TDR and Disposition, detecting missing rows and rejecting absent required projections.
- Added materialize regression coverage rejecting `previous_ci_ids[]` containing a CI from another TCN.
- Added entity-scoped runtime freshness tests for unrelated aggregate generation changes, content changes, producer contract/implementation/static-data changes, and tampered entity digest keys.
- The production-shaped standalone verifier's returned `current_structure_state` is passed unchanged to both `workflow_runtime.py` and `traceability.py`; both accept the same expected identity set with no missing or extra entities.

## Verification

Environment: Python 3.11.5 on Windows.

- Targeted runtime tests (`test_runtime_contract`, `test_workflow_runtime`, `test_traceability_runtime`, `test_materialize_runtime`, `test_ep_vertical_integration`, `test_test_condition_structure`, `test_test_condition_test_data_requirements`): **76 PASS**.
- Runtime suite: `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — **227 PASS**.
- `compileall` for all seven runtime Skill script directories: PASS.
- Deterministic shared tests: **12 PASS**; repository tests: **54 PASS**; deterministic dataset: **14 Skills / 28 cases**.
- Semantic dataset validation: **14 Skills / 51 cases**; shared tests: **27 tests, 25 PASS / 2 Windows symlink-permission skips**; repository tests: **4 PASS**.
- Trigger repository tests: **1 PASS**; exact dataset validation: **14 Skills / 328 queries**.
- Pinned `skills-ref validate`: **14/14 PASS** (UTF-8 mode on Windows).
- Step 2.5 standalone, Markdown round-trip, schema-adapter/materialize path, and qa-workflow integration are covered by passing runtime integration tests, including `test_standalone_evidence_and_qa_workflow_integration` and `test_standalone_evidence_markdown_round_trips_through_cli_verifier`.
- Seven Skill-local `runtime_contract.py` files are LF-normalized identical. SHA-256: `9192e25cd537ea13c5cc28d8b77c47ef70a3b11352db9f9a62f6195168163d98`.
- `git diff --check`: PASS after the report was added.

Semantic candidates, references, rubrics, fixtures, and Skill meaning guidance were not changed. The external Semantic Judge was not rerun because this change is limited to runtime lifecycle, fixed state projection, and Plan synchronization.

## Not run

- GitHub Actions: not run; no push was requested.
- Commit, push, PR update, and merge: not performed.

## Outstanding items

- No known local implementation or verification blockers for this change. Latest remote CI remains unverified until a later push.
