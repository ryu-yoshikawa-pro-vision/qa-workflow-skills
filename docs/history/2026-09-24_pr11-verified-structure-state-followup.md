# PR #11 verified structure state follow-up

## Starting state

- Branch: `feat/deterministic-test-technique-automation`
- Local HEAD: `a04c651e6f5a92c98a75d7d1f00d714a24bfb0f1`
- PR #11 head at start: `a04c651e6f5a92c98a75d7d1f00d714a24bfb0f1`
- PR state: Open / Ready for review / mergeable
- Initial worktree: clean

## Changes

- `verify_runtime_evidence` now returns a fixed `current_structure_state` field on success and `null` on invalid results, including the CLI error response.
- `workflow_runtime.py` and `traceability.py` validate and consume the verifier projection. The production-shaped regression passes one verifier result unchanged to both consumers.
- Carry-forward validation rejects expanded projections: unknown or in-scope TCNs, a TDR owned by an in-scope model, and a Disposition with an unresolved owner. It also checks projection shape, duplicate identities, exact scope-out TR / TCN / model / TC identities, CI ownership under scope-out TCN/model, entity schema, and content fingerprints.
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
- Seven `runtime_contract.py` copies are byte-identical after LF normalization. SHA-256: `31958531a242405d3b89dc5f253fb3f9626813bbe5117e1cd4847018518e82c5`.
- Semantic candidate, reference, rubric, and fixture assets were not changed. The external Semantic Judge was not rerun; existing 24/24 case / 91/91 criteria results are not evidence for this revision.
- `git diff --check`: PASS.

## Remote checks

- GitHub Actions: not run yet; this report records the local pre-push state. Latest-SHA CI results will be recorded in the PR body after push.
- Merge: not performed.
