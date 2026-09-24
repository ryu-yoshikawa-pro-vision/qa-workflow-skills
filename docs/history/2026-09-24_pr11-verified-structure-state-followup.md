# PR #11 verified structure state follow-up

## Starting state

- Branch: `feat/deterministic-test-technique-automation`
- Local HEAD: `a04c651e6f5a92c98a75d7d1f00d714a24bfb0f1`
- PR #11 head at start: `a04c651e6f5a92c98a75d7d1f00d714a24bfb0f1`
- PR state: Open / Ready for review / mergeable
- Initial worktree: clean

## Changes

- `verify_runtime_evidence` returns the fixed `current_structure_state` projection on success and `null` on invalid results, including CLI errors. The TCD projection contains `runtime_results[]`, `carry_forward_entities[]`, and verifier-derived `previous_ci_id_state[]` merged from its strict TCN-scoped materialize results; other Skills return the CI state as an empty array.
- `workflow_runtime.py` and `traceability.py` validate and consume the verifier projection. The production-shaped regression passes one verifier result unchanged to both consumers and confirms exact scope-out CI identity matching.
- Carry-forward validation rejects expanded projections: unknown or in-scope TCNs, CI identities absent from the verifier-derived previous CI state, a TDR owned by an in-scope model, and a Disposition with an unresolved owner. It also checks projection shape, duplicate identities, exact scope-out TR / TCN / model / CI / TC identities, entity schema, and content fingerprints.
- Restored the common Markdown block parser's CRLF-safe identity boundary and added a CRLF artifact regression test.
- Disposition lifecycle tests use producer-valid upstream types: Authority / Product Risk for test-requirement-design, TR for test-condition-design, and TCN / CI / environment requirement / test data requirement for test-case-design. Current-scope rows are replaced or removed by the current result; only scope-out rows carry forward.
- Runtime-v1 previous-artifact rules are enforced and documented: test-analysis, coverage-analysis, and qa-workflow reject non-null previous artifacts; TRD / TCD / test-case-design require the full previous artifact when scope-out carry-forward is required.
- Updated the runtime architecture, identity / workflow, and completion Plans, plus the six runtime Skill instructions.

## Local verification

- Python: 3.11.5
- Targeted modules (`test_runtime_contract`, TRD / TCD / TC structure, workflow, traceability, and runtime workflow integration): **79 PASS**.
- Runtime suite: `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — **233 PASS**.
- Seven runtime Skill script directories and deterministic / semantic eval scripts: `compileall` PASS.
- Deterministic shared tests: **12 PASS**; repository tests: **54 PASS**; dataset: **14 Skills / 28 cases**.
- Semantic dataset: **14 Skills / 51 cases**; shared tests: **27 total, 25 PASS / 2 Windows symlink-permission skips**; repository tests: **4 PASS**.
- Trigger repository tests: **1 PASS**; dataset: **14 Skills / 328 queries**.
- `skills-ref validate`: **14/14 PASS** with `PYTHONUTF8=1` on Windows.
- Standalone evidence, Markdown round-trip, and qa-workflow integration tests: **11 PASS**.
- Seven `runtime_contract.py` copies are byte-identical after LF normalization. SHA-256 after the CI identity projection addition: `2ff0b7708d8d031551f0d4f938f289a35de68aa3281331d377a48b3e6efe51be`.
- Semantic candidate, reference, rubric, and fixture assets were not changed. The external Semantic Judge was not rerun; existing 24/24 case / 91/91 criteria results are not evidence for this revision.
- `git diff --check`: PASS.

## CI identity projection follow-up

A final consumer-validation review found that the TCD canonical input carries only `previous_ci_ids[]` for the current TCN, so consumers could validate CI ownership but could not independently reject an additional plausible CI under an already carried scope-out model. The verifier now projects the strictly merged prior `ci_id_state[]` as `previous_ci_id_state[]`; the shared validator requires the primary carried CI identity set to exactly match its active scope-out CI set. This avoids deriving expected identities from `current_entities[]` and preserves the current-TCN materialize boundary.

- Added workflow and traceability tampering regressions for an extra scope-out CI not present in the verified prior CI state.
- Production-shaped standalone regression asserts that both TCN-scoped materialize CI states appear in the verifier output.
- Targeted suites rerun: **79 PASS**. Runtime suite rerun: **233 PASS**.
- `compileall`: PASS; deterministic shared/repository tests: **12 / 54 PASS**; deterministic dataset: **14 Skills / 28 cases**.
- Semantic dataset: **14 Skills / 51 cases**; shared tests: **25 PASS / 2 Windows symlink-permission skips**; repository tests: **4 PASS**. Trigger repository test: **1 PASS**; dataset: **14 Skills / 328 queries**. `skills-ref validate`: **14/14 PASS** (Python UTF-8 mode enabled).
- Standalone evidence, Markdown round-trip, and qa-workflow integration remained covered by the passing runtime suite. Semantic assets were not changed, so no external Semantic Judge rerun was made.
- `git diff --check`: PASS. GitHub Actions have not been run for this follow-up commit.

## Remote checks

- GitHub Actions: not run yet; this report records the local pre-push state. Latest-SHA CI results will be recorded in the PR body after push.
- Merge: not performed.
