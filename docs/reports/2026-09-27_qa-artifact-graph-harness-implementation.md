# QA Artifact Graph Harness 実装・検証記録

## 対象とbase

- Repository: `ryu-yoshikawa-pro-vision/qa-workflow-skills`
- Branch: `feat/qa-artifact-graph-harness`
- 実装開始時のPR #13 branch HEAD: `e100f664e60321af8224b0b79f0d14a7d1922c3f`
- 実装開始時の`origin/main`（PR #12まで）: `1c8275e635c0bfac9c3f84a264d8ae61ad5dd2ba`
- base選択: ユーザー指示に従い、open中のPR #13 branchへ積み増し。

## Step 0: PR #11 / #12 merge後の再判定

- PR #11のMachine Entity stable identity、content fingerprint、dependency、freshnessは既存の`test-case-design` runtimeがownerです。current TCはstable `TC-NNN`と既存lifecycleで解決します。project-wide current TC inventoryを作る既存helperはありません。Regression helperはownerが解決したprojectionを受け取り、Machine Entityやfreshnessを再実装しません。
- PR #12 manual executionは最初の`scenario.when`操作開始を実開始として扱い、preflight blockだけでは未開始です。rerunは前回artifactとTC refsを引き継ぐ新しいartifact/versionです。E2E executionもowner runtimeのactual attempt、source result、cleanup ownerを参照し、artifact存在を実開始に読み替えません。
- current artifactの既存保存形はMarkdownです。workflow state、knowledge entry、reservationを保存する共通runtime、atomic CAS / create-if-absent adapter、過去revisionの広域取得機能はありません。既存`test-target-inspection`はprovider-native revision / ETag等で条件付き更新できない共有overwriteを拒否します。
- owner executionにsame-workflow pre-start claim / idempotent startはありません。Project Contextは番号付きMarkdown templateで、stable key parserはありません。
- local filesystemで同一filesystem内hard-linkによるatomic create-if-absentが利用できることを検証しました。atomic conditional update / releaseおよび過去revisionの再取得は利用できません。従ってexact-content SHA tokenはidentity確認にのみ使い、CAS条件とは扱いません。CAS / historical refetchが必要な更新、解放、履歴操作は保存先能力が確認できなければblockする方針にしました。
- safe defaultは保存先native primitiveの再利用です。provider CASがない状態でread-compare-unconditional-writeをCAS扱いせず、unsafeなshared mutable operationを開始しません。一般化storage adapter、transaction manager、distributed lock、central scheduler、global mutable manifest / ID counterは追加しません。
- 新規Skillのrequired production helperは各Skill package内の標準ライブラリだけで起動できます。repository共通のeval graderを除き、sibling Skillやrepository root runtimeへ依存しません。Project Contextには明示stable-key markerを追加し、小さなparserでmissing / duplicate / ambiguousをunresolvedにします。

Step 0の確認でPlanの責務境界を変える必要はありませんでした。利用可能なnative primitiveがない保存経路は、Planのfail-closed defaultに従います。

## Plan Step状況

| Step | 状況 | 実装・検証 |
| --- | --- | --- |
| 0. PR #11 / #12再判定 | 完了 | 上記の通り、既存契約と保存先能力を確認。 |
| 1. Skill / vocabulary | 完了 | Regression / Exploratory / QA Knowledgeの3 Skill、owner境界、`qa-workflow` routingを追加。 |
| 2. knowledge / concurrency | 完了 | stable semantic identity、atomic create-if-absent、native CAS要求、workflow state、pre-start claim、resource reservationを追加。primitiveがない更新・解放はblock。 |
| 3. baseline / currentness | 完了 | owner-resolved TC snapshot、revision、lifecycle、complete性、currentnessを分離。 |
| 4. Regression Run plan | 完了 | full / selected scope、membership、batch / resume、routeと補助testware境界を追加。 |
| 5. execution / Activity | 完了 | actual start、source result、blocked / unexecuted、Activity historyを分離。 |
| 6. 修正確認 / FAIL feedback | 完了 | 既存execution Skillへの修正確認routing、owner analysis、別目的Regressionを定義。専用artifact / Skillは追加せず。 |
| 7. Exploratory Testing | 完了 | exploration / investigation、Charter、Observation / Finding、side-effect、cleanup、resume契約を追加。 |
| 8. integrated QA cycle | 完了 | 61 routing fixtureと既存E2E / manual execution契約を回帰確認。 |
| 9. semantic実評価 | 完了 | 実Agent candidate 7件を既存semantic runner + 実Judgeで評価。全7件pass。 |
| 10. relation index gate | 完了 | direct refsとfixed-root deterministic scanで要求を満たすためrelation indexを追加せず。 |
| 11. overall regression | 完了 | PR #11 / #12 runtime・Skill validator・semantic / trigger / deterministic suitesを実行。 |

## 主要変更と検証範囲

- 新規Skill / production helper / validator: `skills/regression-testing`, `skills/exploratory-testing`, `skills/qa-knowledge`。各packageにoutput template、machine template、trigger・deterministic・semantic evalを用意。
- `skills/qa-workflow/scripts/artifact_graph.py`: Project Context stable key、workflow identity/state gate、atomic initial create、pre-start claim、reservation / guarded recovery。
- `skills/qa-workflow`のSKILL、references、workflow-state / Project Context templateを更新。Regression domain判断は`qa-workflow`へ複製しない。
- CI / eval metadata: `.github/workflows/validate-skills.yml`, `.github/workflows/deterministic-output-evals.yml`, `README.md`, `EVALS.md`。19 Skill / 428 trigger query / 38 output eval / 72 semantic caseに同期。
- `tests/skills/evals/deterministic/test_qa_artifact_graph_skills.py`でsnapshot、currentness、batch/resume、membership、actual start、FAIL source result、cleanup、同一entry create競合、state CAS gate、pre-start claim、resource reservation、stable key、helper failure、package portabilityを確認。

## 実行した検証

| コマンド / 検証 | 結果 |
| --- | --- |
| `skills-ref validate`を全19 Skillへ実行（`PYTHONUTF8=1`） | 19/19 valid |
| deterministic output eval構造gate | 38 cases / 19 Skill pass |
| CI repository structure相当のtrigger検証 | 19 Skill / 428 query、split・positive/negative counts pass |
| `python scripts/skills/evals/semantic/validate.py` | 19 Skill / 72 cases |
| `python -m unittest discover -s scripts/skills/evals/deterministic/tests -q` | 12 tests pass |
| `python -m unittest discover -s tests/skills/evals/deterministic -q` | 111 tests pass |
| `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -q` | 271 tests pass（PR #11 / #12 runtime regression含む） |
| `python -m unittest discover -s scripts/skills/evals/semantic/tests -q` | 27 tests pass、2 symlink testsはWindows privilege不足でskip |
| `python -m unittest discover -s tests/skills/evals/semantic -q` | 4 tests pass |
| `python -m unittest discover -s tests/skills/evals/trigger -q` | 1 test pass |
| deterministic grader / validator / production helper `compileall` | 19 Skill validatorおよび対象production helper pass |
| `pnpm run diagnose:hooks`（qa-training-storeのworkspace hook） | `WARN=0 ERROR=0` |

GitHub ActionsはPR branch push後に実行し、この記録作成時点では未確認です。PR headのCI確認とPR本文への結果記録を残作業とします。

## 実Agent candidate + 実Judge

Codex CLIでSKILL / reference / Eval Inputだけを与えてcandidate outputを生成し、`scripts/skills/evals/semantic/run.py`と実Judgeで評価しました。Eval Referenceはcandidate生成には渡していません。

| Skill / case | Verdict | Criterion結果 |
| --- | --- | --- |
| `regression-testing / REG-SEM-003` | pass | 2 pass（rating 4, 4） |
| `regression-testing / REG-SEM-004` | pass | 1 pass（rating 4） |
| `regression-testing / REG-SEM-005` | pass | 1 pass（rating 4） |
| `exploratory-testing / EXP-SEM-002` | pass | 1 pass（rating 3） |
| `exploratory-testing / EXP-SEM-003` | pass | 1 pass（rating 3） |
| `qa-knowledge / KN-SEM-001` | pass | 1 pass（rating 4） |
| `qa-knowledge / KN-SEM-006` | pass | 2 pass（rating 4, 4） |

candidateとjudge result JSONは各Skillの`evals/semantic/candidate_outputs/`に保存しています。初期試行ではRegressionのresidual-risk feedbackとFAIL feedbackが`needs_review`でした。再評価で見つけたEval Input / Reference間のtraceabilityと周辺Regression要求の不足をinputへ明示し、Skillの不足していた出力指示を補ってから再生成・再評価し、最終caseはいずれもpassです。初期候補とjudge結果も同じ場所に保持しています。

最終の`git diff --cached --check`で`EXP-SEM-003` candidateのmetadata行末にあった空白2件を検出しました。metadataを同じ内容のbullet形式に整え、該当candidateを既存semantic runner + 実Judgeで再評価し、verdict `pass`（rating 3）を確認しました。

## Planとの不整合・未達・意図的に未実装

- Planと実コードの契約不整合はStep 0で見つかりませんでした。新規semantic caseの初期inputにはReferenceの根拠が不足していたため、EVALSのhidden requirement禁止に合わせてtraceability / requested Regressionを明記しました。
- local / repositoryにprovider-native atomic conditional update / releaseや歴史revision refetchがありません。これらが必要な状態更新・entry update・reservation recovery・historical lookupは実操作をblockし、provider条件付き操作を要求します。CASを装った代替更新やLLM fallbackはありません。
- relation index、generic storage adapter、transaction manager、central scheduler / distributed lock、central knowledge manifest / global mutable ID counterは追加していません。固定root scan、stable direct refs、storage-native条件の要求で現在のscopeを満たし、追加はPlanが禁止または必要性未実証のためです。
- PR #11 Machine Entity / runtime / freshness、およびPR #12 / E2E execution、result、evidence、rerun lineageは再実装・複製していません。
- fix-confirmation専用Skill / artifact / state、Investigation専用Skillは追加していません。未検証Observation / Findingはcurrent knowledgeへ自動昇格しません。

## PR #13レビュー4件の修正・最終検証

- 対象レビューhead: `5d491b4ec75f941eea2f173d8363039f83250a27`
- 修正commit: `081b6ad07aaf952412453c9b37d26696f32e3220`（PR #13 branchへ通常push）

### 修正内容

1. Regression Activityのactual startと完了を分離しました。logical TCの`executed`はowner executionのactual startだけで決めます。Activity完了にはrequired routeすべてのowner-confirmed `result_finalized`、投影可能なsource result、cleanup完了、unresolvedなしを要求します。結果未確定のrouteがあればActivityは`実行中`となり、同じActivityを後続結果で更新できます。Regression側でPASS / FAIL / 判定不能のtaxonomyから確定状態を推測しません。`REG-D011`も同じ完了条件を検査します。
2. project-local shared resource reservationはacquire前にatomic conditional release能力を要求します。Step 0のlocal filesystem能力では`blocked`となり、予約ファイルを作りません。isolated resourceは`not_required`、取得済みexternal reservationと、create-if-absentおよびconditional releaseの両能力があるproject-local reservationは`reserved`です。既存のowner / expected revision / cleanupによるrelease検証は維持しました。
3. `qa-knowledge.read_entry()`は`^KN-[0-9a-f]{64}$`以外のrefを`invalid_entry_ref`でblockします。parse後はbodyの`entry_ref`とcanonicalized `identity`の両方を要求refと照合し、不一致を`entry_identity_mismatch`でblockします。既存symlink拒否を維持しました。
4. `qa-workflow/SKILL.md`とguidanceに`artifact_graph.py`を必須production helperとして接続しました。開始/resume、mutable operation直前、resource使用前、current成果物完了・再利用前のcheckpointとfail-closed動作を明記しました。pre-start claim pathは`<qa.workflow_state_root>/claims/<content_identity({workflow_ref, operation_ref})>.json`から導出し、`qa.claim_root`は追加していません。helperは`qa-workflow` package内に留めています。

### 追加した回帰テストと特別確認値

- Regression: actual start済み・結果未確定はTC=`executed` / Activity=`実行中`、同一Activityの`update_allowed`を確認。確定済みPASS / FAIL / 判定不能はActivity完了可能で、結果文字列を保持します。required routeの一部だけ未確定でもTCは`executed`、Activityは未完了です。
- Reservation: local filesystemのみは`blocked` / `atomic_conditional_release_unavailable`で、予約ファイルなし。取得済みexternal reservation=`reserved`、isolated=`not_required`、必要な両atomic capabilityあり=`reserved`。
- Knowledge: 正常canonical ref=`current`。malformed / slash・backslash traversal ref=`blocked` / `invalid_entry_ref`でroot外sentinelは不変。body ref / identity不一致は`blocked` / `entry_identity_mismatch`。
- Claim: canonical targetは`<workflow_state_root>/claims/<content_identity({workflow_ref, operation_ref})>.json`。同一operationの並行claimは1件だけacquire。
- Skill contract testはResources、実行checkpoint、処理operation、fail-closed、`qa.claim_root`不在を検証します。

### 最終検証

| コマンド / 検証 | 結果 |
| --- | --- |
| focused deterministic: `python -m unittest discover -s tests/skills/evals/deterministic -p 'test_qa_artifact_graph_skills.py' -v` | 26 tests pass |
| deterministic: `python -m unittest discover -s tests/skills/evals/deterministic -v` | 114 tests pass |
| runtime: `python -m unittest discover -s tests/skills/runtime -p 'test_*.py' -v` | 271 tests pass |
| shared deterministic: `python -m unittest discover -s scripts/skills/evals/deterministic/tests -v` | 12 tests pass |
| `python scripts/skills/evals/semantic/validate.py` | 19 Skills / 72 cases pass |
| semantic runner tests: `python -m unittest discover -s scripts/skills/evals/semantic/tests -v` | 27 pass、2 Windows symlink privilege skips |
| repository semantic: `python -m unittest discover -s tests/skills/evals/semantic -v` | 4 tests pass |
| trigger: `python -m unittest discover -s tests/skills/evals/trigger -v` | 1 test pass |
| `skills-ref validate`（19 Skill） | 19/19 valid |
| CIと同じ対象群でのPython `compileall` | pass |
| `git diff --check` | pass |
| 影響caseの実Agent candidate + 既存semantic runner + 実Judge（`REG-SEM-004`のみ） | pass、rating 4。結果確定済みFAILと未開始blocked routeを区別し、source resultを保持 |

修正commit `081b6ad07aaf952412453c9b37d26696f32e3220` に対するGitHub Actions 3件はすべてsuccessです: [Validate Agent Skills](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/36295746716)、[Validate Deterministic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/36295746695)、[Validate Semantic Output Evals](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/actions/runs/36295746709)。PR #13の最終headの状態は[PR checks](https://github.com/ryu-yoshikawa-pro-vision/qa-workflow-skills/pull/13)で確認します。

### Plan整合・未達

- 今回の4修正でPlanとの責務境界・保存モデル変更はありません。Step 0で記録したlocal filesystemの事実（atomic create-if-absentあり、atomic conditional update / releaseなし）は変更していません。
- Regressionはowner-confirmed `result_finalized` projection factを受け取り、結果taxonomyを複製しません。shared reservationはconditional release capabilityがないlocal保存先でfail-closedです。
- 今回指定された4件、ローカル検証、修正commit上のCIに未達事項はありません。意図的に未実装の対象は既存Plan節の記載どおりです。
