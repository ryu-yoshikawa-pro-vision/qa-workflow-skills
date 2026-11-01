# PR #17 QTS再評価とtarget integrity検証

## 結論

- 開始HEADは`12882a0cb89b7ebbda4f9fe2cea96b77517026e8`。固定QTS source revision `84ce165493649550832731a60cf436f8ae29c56b`から、同じscenario・task・Skill package・生成promptで開発用subagent評価を2回実施した。
- 2試行とも準備時と実行後のtarget integrity検査は成功し、target外への変更、`__pycache__`、秘密形式の出力は検出されなかった。Evaluator-only資料はtarget packageに含まれないが、共有workspaceのためAgentからの物理的な読取拒否は成立していない。
- `gpt-6-luna / max / fork_turns=none`を両subagentに指定した。Codex側の実効model/build telemetryはなく、実効設定は未検証。
- r5の24時間境界質問漏れは今回の両出力で再現しなかった。最終在庫不足の正確な期待結果は1試行目で根拠なくSPECへ昇格し、2試行目ではQ/UNKNOWNとして適切に局所化された。単発の生成不備は確認したが、Skill固有の再現性ある原因は確定できず、Skillは変更していない。
- r5のTCN過剰blockedは2試行目の有効なcondition runtimeで再現しなかった。2試行目は正常な拒否・processing再開・TEST-SUCCESSを別のCoverage Itemとしてmaterializeし、最終在庫不足の詳細だけを未確定として残した。
- r5のTC-016未根拠成功期待は、両試行ともcase生成が完了しなかったため今回再評価できない。新しいケースを捏造して補わず、未評価として残す。
- 変更は評価用Python bytecode抑止とその回帰テスト、Plan/README、今回の報告に限定した。QTS製品、仕様、Skill、expected、grader、Judge fixtureは変更していない。
- これは開発用実動作検証であり、正式runner・独立Judge・正式QTS受入ではない。

## 固定した実行条件と証拠

| 項目                             | 両attemptの条件                                                                                                                   |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Evaluator / Skill source         | `12882a0cb89b7ebbda4f9fe2cea96b77517026e8`                                                                                        |
| Evaluator working diff           | `sha256:9b004a1a85ba5665c365c078d2edaa2420bbf13819415032f3267c293abfd4e8`                                                         |
| Target source                    | `84ce165493649550832731a60cf436f8ae29c56b`。source checkout clean                                                                 |
| Scenario / task                  | `qa-training-store-checkout-payment-web-v1` / task hash `sha256:a40343bce1d62d727c236cdc759d125c1b77f7375b7786d9af7e0a65bc938e98` |
| Generation prompt                | hash `sha256:8b29164e921ae00064734aeecf7bdaf6f50b7a79046424c02a90b8fd4ede4f4f`                                                    |
| Skill package                    | 215 files、`evals/`除外、fingerprint `sha256:28162d13deecf08731ade613914be8b4c210c8003ddecd9a391dffe150cd7cea`                    |
| Requested subagent settings      | `gpt-6-luna / max / fork_turns=none`                                                                                              |
| Effective model / build          | telemetryなし。未検証                                                                                                             |
| Evaluation mode                  | 現在のCodex sessionから起動したsubagent。開発用評価                                                                               |
| Attempt 01 synthetic target HEAD | `5e6d7008357f060a0b896c75b7e0b38d250767e6`                                                                                        |
| Attempt 02 synthetic target HEAD | `a48ac3c2f76a4d91bbbae85d993335be7a649300`                                                                                        |

実行前にsource manifest 902 files、各sanitized target manifest 1,120 filesを記録した。synthetic Git repositoryはそれぞれtarget rootと一致し、1 commit・remoteなし。synthetic HEADは固定source SHAとは異なる評価用baselineであることを生成promptと`AGENTS.md`で明示した。正解、rubric、grader、Judge fixtureはAgent向けtarget packageへ配置していない。ただし親Agentとsubagentは同じworkspace権限を持ち、物理read-denialは検証していない。

全raw output、runtime request/result、各target baseline manifest、attemptごとのparent validation、実行条件は、Git管理外の`.agent-eval-runs/pr17-qts-quality-batch-20261102-preflight/`に保存した。`evaluator-private/`およびattempt directoryは0700、private JSON記録は0600である。試行後にtarget sourceの差分、symlink、通常file以外のentry、秘密形式の出力、bytecodeを検査した。

## attempt別結果

### attempt-01

- 9件のQA成果物と14 routing rowを生成した。`artifact-index.json`はscenarioのfield contractには合致したが、判定は`needs_review`。
- routing内訳はexecuted 3、incomplete 5、blocked 1、scope外skipped 5。5件のscope外skipはlive UI inspection、test execution、E2E各工程であり、固定scenarioの分析・設計scopeに対して妥当。
- `test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`のruntime verifierは`valid=false`。root/runtime unitやcurrent downstream Entityが不足し、test-case表はheader-only。coverage traceabilityはempty scopeで未解決。coverage verifierは一度失敗し、見出し修正後の再captureはしていない。
- `spec-analysis`成果物のverifierは`valid=true`でAuthority Entity 12件を返した。ただし、最終在庫不足の具体的Payment / Order状態を`SPEC-003`として記述し、Question Analysisから同じ未確定事項を漏らした。固定仕様は当該tupleを明記せず、spec-analysis Skillは未定義動作を`SPEC`へ昇格させない契約を持つため、この出力は意味上不適合。
- 24時間境界は`Q-001 / UNK-001`として質問・影響範囲を記録した。Payment結果とURL不一致は`Q-002 / UNK-002`。
- qa-workflow runtime evidenceは`workflow-runtime`が`invalid_input / blocked`（`current_structure_state`不足）。別のverifierが`valid=true`でも、workflow完了や`can_complete=true`を意味しない。
- artifact manifestは作業用Python/JSON 4ファイルを`unregistered_or_internal`と分類した。どれもQA artifactとして登録されておらず、ValidatorはPASSにしなかった。
- parent validation: 9 artifacts、14 routing rows。target integrity `unchanged=true`、`__pycache__` 0、secret-shaped output 0。

### attempt-02

- spec analysis、question analysis、test analysis、test requirements、test conditionsを作成。test-analysis / requirement / conditionの保存済みverifier resultはすべて`valid=true`。test-condition runtimeは6 TCN、6 model、30 CI、42 Entity、13 runtime unitを返した。
- test conditionsはTEST-SUCCESSかつ在庫十分、明確なPayment拒否、processing開始・resumeを別Coverage Itemへ分けた。最終在庫不足の厳密な終端状態と回復UIだけを`Q-002 / UNK-002`として局所化した。24時間境界も`Q-001 / UNK-001`として維持した。runtime materializationしたscopeでは、r5のTCN過剰blockedは再現しなかった。
- case helperの`--help`呼出しは誤ったworkdirでprocess起動前に失敗した。失敗記録を保存し、再試行はしていない。`test-case-design`はblocked、coverageは未開始、最終qa-workflow runtime gateは未実行。test-case表にTC-016がなく、REV-002を評価できない。
- Agent生成の`artifact-index.json`はscenario contractと不一致（`schema_version`がJSON string、artifact/routing rowのfield不足、runtime記録をartifactとして列挙）。固定`validate_artifact_index()`は`needs_review / artifact_index_schema_mismatch`を返した。8つのMarkdownはvalidator上未登録として分類された。親側でindexを修正してPASSにしていない。
- helper入力のraw scalar valueが一度`invalid_input`となった記録があり、型付き値でmaterializeしたrequest/resultを別に保存した。これはhelper入力契約の失敗で、生成されたQA成果物のPASSとは別に記録した。
- case helper失敗、typed-value failure、最終routing、QA artifactsをすべてattempt-02のtargetに保存した。
- parent validation: target integrity `unchanged=true`、`__pycache__` 0、secret-shaped output 0。3 verifier invocationのpath・request/result hashはparent側で照合できたが、subagent tool transcriptがなく呼出し履歴の独立確認はできない。

## r5所見の再評価

| 所見                                      | 今回の観測                                                                                                                                                                                             | 判定                                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| REV-001: TCN-005が既知経路までblocked     | attempt-02のcurrent materializationは明確拒否、processing、TEST-SUCCESSをそれぞれcoverage化し、最終在庫不足の厳密な結果だけを局所UNKNOWNにした。attempt-01もdraftでは各経路を分けたがruntime invalid。 | attempt-02の有効runtime scopeでは再現せず。全case downstreamの成立は未確認               |
| REV-002: TEST-SUCCESSなしでTC-016成功期待 | 2試行ともtest-case generationが完成せず、TC-016相当のruntime caseを生成・検証していない。                                                                                                              | 未評価。改善とも再現とも判定しない                                                       |
| 24時間境界質問漏れ                        | 両attemptで`Q-001 / UNK-001`を作り、等号境界だけを局所化。                                                                                                                                             | 今回再現せず                                                                             |
| 最終在庫不足の具体tuple                   | attempt-01で未定義tupleをSPECとして断定。attempt-02では同じ意味範囲をQ/UNKNOWNへ分類し、厳密な結果はblocked。                                                                                          | 1/2の意味的不適合。Agent出力の揺れは確認したが、Skill起因の再現性は未確定。Skill修正なし |
| artifact-index / output classification    | attempt-01はindex contract validだがnoncompleted routing・未登録helper fileによりneeds_review。attempt-02はindex schema違反で8 markdownが未登録扱い。                                                  | 2試行ともPASSではない。既存validatorが非適合を検出。Skill根本原因は未確定                |

`docs/spec/features/checkout-and-payment.md`はTEST-SUCCESSだけが成功確定を行い、明確なPayment失敗では在庫不変、processing中のRetry / Cancel禁止を定める。AC-CHECKOUT-003は最終在庫不足時もOrder / Payment / Inventory / Historyの整合を要求するが、厳密な終端tupleを列挙しない。現在QTS正本に追加回答はなく、`can_complete=false`相当の未解決状態を維持した。QTS製品仕様・Product Code・既存Product Testは変更していない。

## 評価環境の修正

r5でsanitized targetに`__pycache__`が作られた経路に対して、Python helper実行を抑止する共通契約を追加した。

- `target_workspace.py`とQTS generation promptは、Agentがtarget内helperを`PYTHONDONTWRITEBYTECODE=1 python -B`で起動するよう指示。
- `verifier_capture.py`はruntime contractを`python -B`で起動し、実行記録にもflagを保存。
- WSL2 outer bwrap environmentへ`PYTHONDONTWRITEBYTECODE=1`を渡す。正式runnerは今回起動しておらず、この部分はunit test/static checkのみ。
- focused regression testはdummy helper import後に`__pycache__`がないこと、target instructions、prompt、launcher envを確認する。

今回の2 targetでbytecode生成は検出されなかった。未登録helper fileはattempt-01だけで出て、attempt-02では出なかったため、再現性あるprompt defectとは確定せず、artifact kindやvalidatorを緩和していない。

## 検証・残条件

- Focused Agent evaluator tests: 78 tests、1 skipped、その他passed。
- Agent evaluator suite: 173 tests、2 skipped、その他passed。
- `compileall`: pass。bytecodeは`/tmp/pr17-qts-compilecache-20261102`へ分離。
- dprint check、`git diff --check`: pass。
- Ruff: local Python環境にRuffがなく未実行。GitHub Code Quality CIで確認する。
- Docker commandは利用可能でなく、QTS production verifierのpinned-container replayは未実行。runtime result JSONはcaptureとhashを照合したが、fixed Docker replay / tool transcriptは未確認。
- 正式WSL2 runnerは認証refresh永続化・非協調process競合が未解決のためfail-closedのまま。Launcher flagを解除していない。
- QTS Judge fixture 11件は未承認（人間レビュー待ち9件、決定論的レビュー待ち2件）。独立Judgeは起動していない。
- 独立Judge、実効model/build telemetry、Evaluator-only情報への物理read-denial、正式runnerのrun-specific isolation evidenceは未成立。
- 完了したのは2つの開発用QTS subagent実行とtarget integrity確認であり、QA workflowのcompletion、QTS品質PASS、正式な独立評価は未達。
