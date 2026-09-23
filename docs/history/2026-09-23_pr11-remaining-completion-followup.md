# PR #11 remaining completion follow-up — 2026-09-23

## Start state

- Branch: `feat/deterministic-test-technique-automation`.
- Local HEAD at start: `c2f85961274a63e7a57cce8e44c9fde202d39c62`.
- PR branch remote HEAD at start and final recheck: `c2f85961274a63e7a57cce8e44c9fde202d39c62`.
- The existing local changes were preserved. No reset or overwrite was performed.
- The previous follow-up report and the criterion-level analysis appendix were preserved:
  - `docs/history/2026-09-23_124500_pr11-review-regression-followup.md`
  - `docs/history/2026-09-23_pr11-semantic-judge-criteria-starting-state.md`

## Context schema and dependency contract

The Plan fixed the `test_analysis_context` content schema without identity fields for the Authority and Product Risk entities that its dependency contract required. Natural-language content such as `residual_risks[]`, `blockers[]`, and `test_focus_items[]` cannot identify those entities deterministically, so inferring dependency edges from those fields would violate the existing contract.

The canonical context schema now adds:

```text
authority_refs[]  # unique string Authority Entity identities, canonical order
risk_refs[]       # unique string Product Risk risk_id values, canonical order
```

These fields are synchronized in:

- `_02_runtime-architecture-and-contracts.md`: context schema and semantic dependency list.
- `_03_artifact-processing-and-script-contracts.md`: input schema and context dependency resolution rules.
- `_05_evaluation-ci-implementation-order.md`: regression conditions.
- `_05_implementation-order-and-completion.md`: applicable completion condition.

Only the `test_analysis_context` schema listings and their dependency statements were updated. No other Plan inconsistency was found in the reviewed sections.

`analysis_entities.py` keeps the required order: change graph / environment requirements, Product Risk, then Technique Selection / context. Both modes require every `authority_refs[]` entry to resolve to a current Authority Machine Entity; artifact mode resolves the artifact set, while direct mode resolves only explicitly passed current entities. Unknown refs fail validation, and the runtime never synthesizes an Authority Entity. Context `risk_refs[]` resolve only to Product Risks created during the same invocation; the runtime generates their content fingerprints and does not accept caller-supplied fingerprints. Duplicate or unknown refs fail validation. Natural-language fields are not used as dependency identities.

Regression coverage in `tests/skills/runtime/test_test_analysis_entities.py` verifies empty, Authority-only, Risk-only, combined, and multiple-Risk refs; canonical-order independence; Authority and Risk fingerprints on dependencies; duplicate / unknown / missing-ref rejection in artifact and direct modes; caller fingerprint injection rejection; referenced-content stale propagation; and no stale propagation from unreferenced Risk or Authority changes. The runtime suite, including these cases, passed.

## Semantic Judge analysis and changes

The starting Judge result was 4 pass / 15 needs_review / 5 fail. The 20 non-PASS cases contained 44 non-PASS criteria: 31 needs_review, 11 fail, and 2 not-evaluable. The detailed criterion appendix records Skill, case and criterion IDs, criticality, rating, evaluability, Judge reason and evidence, candidate and reference evidence, rubric requirement, cause, and action. Its retrospective addendum also records the current Eval input / Reference / rubric, latest candidate evidence, latest Judge evidence, and final classification for each of the 12 initially classified Reference / Eval criteria.

Starting cause counts were:

| Initial cause | Criteria | Cases |
| --- | ---: | ---: |
| Candidate defect | 32 | 15 |
| Reference / Eval mismatch | 12 | 8 |
| Context schema effect | 0 | 0 |
| Rubric mismatch | 0 | 0 |
| Judge false / unstable | 0 | 0 |
| Other | 0 | 0 |

Some cases had more than one cause; for example, TCN-SEM-006 and TCN-SEM-010. The follow-up review found that all 12 initial Reference / Eval criteria (8 cases) were genuine fixture/specification gaps, not candidate defects: the old Eval input omitted facts needed to evaluate the reference requirement, or the expected reference detail was too general to map exactly to the fixture. Those Eval inputs and, where necessary, references were made explicit against Plan / current Skill contract. Therefore the prior wording that “references and rubrics were not changed” was too broad: several Eval inputs and four references changed, but no criterion was removed, no criticality or pass threshold was lowered, and the normative requirement was not changed to match a candidate. The global `SEM-TCN-002` rubric description was also clarified to distinguish product-behavior technique selection from deterministic adapter/materialization validation; this was not a rubric defect among the initial 44 criteria and did not change criticality or threshold. The 12 historical issues are resolved: latest candidates pass all 12, and current unresolved Reference / Eval mismatches = 0. See the starting-state appendix retrospective audit for per-criterion evidence.

After the prior targeted Skill fixes, an intermediate valid batch had four non-PASS criteria:

| Skill / case / criterion (criticality, rating, evaluable) | Candidate evidence | Reference and rubric requirement | Cause and action |
| --- | --- | --- |
| test-analysis / RISK-SEM-005 / SEM-RISK-005 (noncritical, 2, evaluable) | “Random Testingを採用し…再現可能な探索”; separate systematic coverage was deferred until input classes were known. | Reference requires fixed seed and separate deterministic boundary / explicit-requirement coverage. Rubric asks whether the selected technique fits the structure. | Candidate defect. Generic Random Testing guidance now requires fixed seed and separate systematic coverage. |
| test-analysis / RISK-SEM-006 / SEM-RISK-004 (critical, 2, evaluable) | Focus named the relation between input and re-encoded output and deferred specific follow-up generation; it did not state the whole source × follow-up set or that one relation check is insufficient. | Reference requires all candidate pairs in focus/depth and says one relation check is not sufficient. Rubric requires risk-aligned focus and depth. | Candidate defect. Generic Metamorphic guidance now preserves all candidate pairs and rejects one-example closure. |
| test-condition-design / TCN-SEM-011 / SEM-TCN-003 (critical, 2, evaluable) | The runtime table showed a `generation fingerprint` and `catalog version` column, but no exact `static_data_versions.ui_pattern_catalog` field. | Reference requires retaining that exact field and its catalog version. Rubric asks whether coverage criteria are sufficient. | Candidate defect. Generic UI-pattern guidance now requires the exact runtime field, catalog version, canonical pattern key, and all candidate keys. |
| test-condition-design / TCN-SEM-013 / SEM-TCN-003 (critical, 2, evaluable) | CI03 says the requirement intersection is empty and “conflictとして扱う”; it does not say to reject the merge or suppress the merged CI. | Reference requires rejecting a merge when the union intersection conflicts. Rubric asks whether coverage criteria are sufficient. | Candidate defect. Generic materialization guidance now says conflict rejects integration and creates no merged CI. |

No reference, rubric, or Judge changes were made for these findings. All affected candidates were generated again from current Skills and their inputs, not hand-edited.

One intermediate Judge batch was discarded: the generated `test-analysis` marker output had not yet been extracted into the candidate files when that batch was launched, so it evaluated the older saved five candidates. The mismatch was found by checking Judge evidence against the candidate text. Its 22 / 2 result is not used as evidence for the latest candidates. The five `test-analysis` outputs were then extracted from the generated output and the full 24-case batch was rerun.

That valid batch produced 23 pass / 1 needs_review / 0 fail. For TCN-SEM-007 / SEM-TCN-003, the criterion was critical, rating 2, evaluable=true. The Judge reason was that the candidate listed `guest × private` as Rule `TCN-SEM-007-CI02`, which could conflict with the requirement not to treat it as a Coverage Item. Candidate evidence was `| TCN-SEM-007-CI02 | guest | private | 成立不能（SPEC-017） | 対象外のassignment。拒否actionを割り当てない |`. The Reference says the Authority-defined infeasible assignment must not become an action-bearing rule or Coverage Item. Rubric `SEM-TCN-003` (critical) asks whether coverage criteria are sufficient. This was a candidate defect, not a Reference, rubric, context, or Judge issue.

The Decision Table guidance in `skills/test-condition-design/references/coverage-techniques.md` now says that an infeasible assignment is constraint evidence, not an executable rule or Coverage Item; it receives no CI ID and is excluded from the coverage population. TCN-SEM-007 was generated again from the current Skill and input. Its rerun scored 4/4 criteria PASS. The related TCN-SEM-008 candidate was also regenerated and rerun because it carries an infeasible tuple constraint; its latest candidate and Judge result passed. No Eval reference or rubric was changed.

After the direct-mode unknown-Authority rule was clarified, the five `test-analysis` candidates were regenerated from the latest Skill and reevaluated. Four passed; RISK-SEM-007 / SEM-RISK-005 (noncritical, rating 2, evaluable=true) remained needs_review. The Judge reason was that the candidate omitted the reachable / unreachable production distinction and treated specific inputs and criteria as blocked. Candidate evidence was “Syntax-Based Testingを採用する…追加productionに適合する構文の受理と、仕様上の構文エラーの検出を重点化” and “production定義…mutationの具体内容が提示されていない…具体的な入力とPASS / FAIL基準の確定はブロック中.” The Reference requires distinguishing reachable and unreachable productions and not silently excluding the latter. Rubric `SEM-RISK-005` (noncritical) asks whether the selected technique fits the problem structure. This is a candidate guidance gap: reachability is relevant to test focus and can be handed off unresolved without inventing a grammar or invalid input. It is not a context-schema effect, Reference / Eval mismatch, rubric mismatch, or Judge error.

`skills/test-analysis/references/guidance.md` now says Syntax-Based Testing must distinguish reachable and unreachable productions, must not count or silently omit unreachable productions, and must hand off unknown reachability without inventing grammar examples or invalidity. RISK-SEM-007 was generated again from the current Skill and input. The candidate now identifies reachability as a test focus, does not count unreachable production as coverage, and keeps missing grammar details unresolved. Its three applicable criteria scored 3/3 PASS.

The final result set uses the five latest `test-analysis` results (RISK-SEM-007 from round 8; RISK-SEM-003 through RISK-SEM-006 from round 7), the 17 unaffected passing candidates from the valid full batch, and the rerun current candidates for TCN-SEM-007 and TCN-SEM-008. All 24 latest candidate cases and all 91 applicable criteria pass:

| Group | Cases | Result |
| --- | --- | --- |
| test-analysis | RISK-SEM-003 through RISK-SEM-007 | 5/5 pass |
| test-case-design | TC-SEM-002 | 1/1 pass |
| adversarial-review | REV-SEM-003 through REV-SEM-008 | 6/6 pass |
| test-condition-design | TCN-SEM-003 through TCN-SEM-014 | 12/12 pass |
| **Total** | **24 cases / 91 criteria** | **24/24 cases; 91/91 criteria pass** |

Candidate generation used `codex.cmd exec --ephemeral --sandbox read-only -C <repo> -` with only current Skill instructions and the relevant Eval input (plus current runtime output where the case requires it). Latest prompt files were `%TEMP%\pr11-context-semantic-round7-20260923\test-analysis.prompt.txt` (RISK-SEM-003..007) and `%TEMP%\pr11-context-semantic-round8-20260923\RISK-SEM-007.prompt.txt`; the affected TCD prompts for TCN-SEM-007 / TCN-SEM-008 are in round 6. Judge evaluation used this existing runner invocation for each case:

```text
python scripts/skills/evals/semantic/run.py --skill <skill> --eval-id <eval-id> --output <candidate.md> --judge-command <APPDATA>\npm\codex.cmd exec --ephemeral --sandbox read-only -C <repo> -
```

No provider adapter was added. The full-batch runner was `%TEMP%\pr11-context-semantic-round6-20260923\judge-batch.py`; focused regeneration / Judge runs are recorded under `%TEMP%\pr11-context-semantic-round7-20260923\` and `%TEMP%\pr11-context-semantic-round8-20260923\`. The final 24 per-case results are under `%TEMP%\pr11-context-semantic-round8-20260923\judge-results-final\`.

## Latest Agent runtime smoke

Both smoke runs used the current Skill revision, Python 3.11.5, and Agent-generated input / Markdown.

### test-analysis

`risk_matrix.py → technique_candidates.py → analysis_entities.py → Machine Entities → Markdown save / reload → semantic dependency preflight → current script rerun` passed in artifact mode. The context carried the current Authority fingerprint for `SPEC-CHECKOUT-001` and the same-invocation Product Risk fingerprint for `R-001`; Technique Selection also carried its current `R-001` fingerprint. Same-input generation fingerprint and payload were reproducible; Markdown round-trip passed; preflight was current. Changing referenced Risk or Authority made the context stale. Changing unreferenced Risk or Authority kept it current. A dummy secret was not persisted.

### test-condition-design

The current `schema_cases.py` result was stable across two invocations. The Agent-generated Markdown retained the same generation fingerprint and exactly preserved the four runtime-produced `derived.test_data_requirements` rows (operators: boolean, enum, range). Required-property, enum, and BVA skeletons were present. The smoke output and runtime fingerprint matched.

## Local verification

All checks below were rerun after the context and Skill guidance changes using Python 3.11.5:

- `compileall` for the seven specified Skill script directories: PASS.
- Runtime tests: 186 PASS.
- Deterministic shared tests: 12 PASS; repository tests: 54 PASS.
- Semantic dataset validation: 14 Skills / 51 cases PASS.
- Semantic shared tests: 27 PASS; repository tests: 4 PASS.
- Trigger tests: 1 PASS; dataset: 14 Skills / 328 queries.
- Deterministic dataset: 14 Skills / 28 cases.
- `skills-ref validate`: 14/14 PASS (run with Python UTF-8 mode on Windows).
- Seven `runtime_contract.py` copies are byte-identical after LF normalization; SHA-256: `1d89a68c1e3687a8a6fa733af52a7c0604958e415d0e64876748144aa0c53712`.
- Step 2.5 standalone and `qa-workflow` integration tests passed, including the standalone Markdown round-trip and workflow acceptance cases.
- `git diff --check`: exit 0. Git emitted only its working-copy LF-to-CRLF normalization warnings.

The semantic shared suite skipped exactly these two symlink cases because the Windows environment returned WinError 1314 (symlink privilege unavailable):

- `test_symlink_escape_raises`
- `test_cases_directory_symlink_escape_raises`

The existing skip behavior and production code were not changed.

## Plan recheck and GitHub Actions on implementation commit

- Context canonical schema and dependency contract are aligned.
- Implementation completion conditions: 0 unmet.
- Plan deviation: none found.
- Implementation/test commit: `18098995376190b14778dc04c55c1d0aae7f3636` (`fix: address deterministic runtime review findings`).
- Local HEAD and PR head were both `18098995376190b14778dc04c55c1d0aae7f3636` when the following pull_request workflows completed:

| Workflow | Run ID | Result |
| --- | ---: | --- |
| Validate Agent Skills | 35852216520 | success |
| Validate Semantic Output Evals | 35852216454 | success |
| Validate Deterministic Output Evals | 35852216435 | success |

- Ubuntu symlink check: run 35852216454, job `semantic-output-evals`, step `Run Semantic Eval shared runtime tests`. Both `test_cases_directory_symlink_escape_raises` and `test_symlink_escape_raises` were discovered and reported `... ok`; the shared suite ran 27 tests and finished `OK` with no skips.
- Saved external Semantic Judge set: current latest candidate set 24/24 cases, 91/91 criteria PASS; needs_review=0, fail=0, not_evaluable=0. The historical 12 Reference / Eval causes are resolved; current unresolved mismatch count is 0. Criterion evidence and the corrected cause record are in `docs/history/2026-09-23_pr11-semantic-judge-criteria-starting-state.md`.
- Windows semantic shared suite still skips the same two symlink tests because of WinError 1314; Ubuntu execution above confirms both tests pass when symlink creation is available.
- This report records CI run IDs for the implementation/test commit. The report-only follow-up head must also pass all three workflows before the PR description is updated.

## GitHub PR body proposal (not yet applied; update after latest-head CI)

> ## 実装状況
>
> runtime-v1の実装と回帰修正を反映しました。`test_analysis_context`は明示的なAuthority / Product Risk参照を保存し、current Machine Entityへの依存とfreshnessを検証します。Decision Tableの成立不能assignmentはCoverage Itemから除外します。
>
> ## 検証
>
> Python 3.11.5でruntime 186件、deterministic 66件、semantic dataset 14 Skill / 51 case、trigger dataset 14 Skill / 328 query、deterministic dataset 14 Skill / 28 case、`skills-ref validate` 14/14を確認しました。最新candidateの外部Semantic Judgeは24/24 case、91/91 criteria PASSです。`test-analysis`と`test-condition-design`のAgent runtime smokeもPASSしました。GitHub Actionsは最新headで3 workflow成功、Ubuntu symlink testsは2/2 PASSです。
>
> ## 残課題
>
> 本PRのPlan完了条件に対する既知の未達なし。

## Git operations

- Commit `18098995376190b14778dc04c55c1d0aae7f3636`: performed (normal commit).
- Push: performed; local HEAD = PR head at the time of the first GitHub Actions check.
- GitHub PR body update: not yet performed; wait for CI on the documentation-only report commit's latest head.
- Merge / branch deletion / issue or PR close: not performed.
