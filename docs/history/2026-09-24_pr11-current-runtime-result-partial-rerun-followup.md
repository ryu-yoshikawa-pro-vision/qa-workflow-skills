# PR #11 current runtime result and partial rerun follow-up

## Starting state

- Repository: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- Branch: `feat/deterministic-test-technique-automation`
- Local HEAD: `fb7d1202c76ad4cf739dc29e1a41cc7e789c3882`
- PR #11 head: `fb7d1202c76ad4cf739dc29e1a41cc7e789c3882`
- PR state at start: Open / Ready for review / mergeable
- Working tree at start: clean

## Changes

### Current rerun result is authoritative

- `workflow_runtime.py` continues using saved `runtime_units[]` to check runtime evidence identity and missing / extra units. It now uses `current_runtime_units[]` for unsupported closure, target disposition closure, materialize completion, and other current semantic state.
- Shared runtime freshness compares the saved consumer projection with the fixed projection of the current rerun. A same-generation result difference marks the saved row stale and blocks completion.
- Added `result_fingerprint`, computed as SHA-256 over the canonical full Machine Runtime Result envelope. It is distinct from `generation_fingerprint`; output changes do not alter generation semantics.
- `_runtime_unit_result_row()` uses the existing `runtime_unit_row()` builder and projects materialize payload state (`model_completion`, target mappings, target dispositions) before comparing `current_structure_state.runtime_results[]` with current rerun rows. Payload tampering with unchanged generation is rejected.
- `traceability.py` uses the same shared saved/current result freshness check and continues using current rerun rows for semantic closure and completion decisions.

### Disposition-only partial rerun

- `verify_runtime_evidence` now requires the strict boolean `partial_rerun` request field.
- `test-requirement-design`, `test-condition-design`, and `test-case-design` require `partial_rerun=false` with `previous_artifact_markdown=null` for full builds, and `partial_rerun=true` with the complete prior artifact for every partial rerun. The verifier strictly validates the prior artifact even when no primary ID is out of scope, so a scope-out Disposition cannot disappear through a null previous artifact.
- `test-analysis`, `coverage-analysis`, and `qa-workflow` require `partial_rerun=false` and `previous_artifact_markdown=null` in runtime-v1.
- Legacy initial promotion remains a normal full snapshot and is not marked as a partial rerun.
- Updated the four relevant runtime / artifact-processing Plans and six Skill instructions to document the fixed lifecycle and current-result boundary.

## Local verification

- Python: **3.11.5**
- Targeted runtime modules (runtime contract, workflow, traceability, workflow integration, EP vertical integration, TRD / TCD / TC structure): **88 PASS**.
- Full runtime unit / integration suite: `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` — **242 PASS**.
- Compileall for all seven runtime Skill script directories and deterministic / semantic eval code: **PASS**.
- Deterministic shared tests: **12 PASS**; repository tests: **54 PASS**; output dataset: **14 Skills / 28 cases**.
- Semantic dataset: **14 Skills / 51 cases**; shared tests: **27 total, 25 PASS / 2 skipped** on Windows because symlink privileges are unavailable; repository tests: **4 PASS**.
- Trigger repository test: **1 PASS**; trigger dataset: **14 Skills / 328 queries**.
- `skills-ref validate`: **14/14 PASS** with Python UTF-8 mode enabled.
- Step 2.5 standalone, Markdown round-trip, schema-adapter / materialize, and qa-workflow integration: **PASS** in the runtime suite, including `test_standalone_evidence_and_qa_workflow_integration`, `test_standalone_evidence_markdown_round_trips_through_cli_verifier`, and `test_ep_standalone_runtime_is_accepted_by_qa_workflow`.
- Seven `runtime_contract.py` copies are identical after LF normalization. SHA-256: `da920a12e381390d0fc90bfbd4924e76af29546794c44540fb1751149e77f7fc`.
- `git diff --check`: **PASS**.
- Semantic candidate, reference, rubric, fixture, and semantic judgment responsibility were not changed. The external Semantic Judge was not rerun; prior 24/24 case / 91/91 criterion results are not evidence for this revision.

## GitHub Actions and Git operations

- GitHub Actions for this revision have not been run; the changes are not pushed yet.
- This report records local verification through the current working-tree revision. After push, the latest-SHA workflow runs and their run IDs will be recorded in the PR body, not by creating a CI-only follow-up commit.
- Commit, push, PR body update, merge, branch deletion, and PR / Issue close have not been performed at report creation time.
