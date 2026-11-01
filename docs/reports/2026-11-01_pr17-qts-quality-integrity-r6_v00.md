# PR #17 QTS 品質所見と評価記録の検証

## 結論

- 開始HEADは`32008149d6204523d2e9deaf09e88866627a7b0b`。PR #17はOPENで、GitHub上の対象HEADも同一だった。
- r5の内容所見（REV-001、REV-002、24時間境界質問の欠落）は固定QTS revisionの仕様と成果物で確認できる。ただし各所見は1回の生成に基づく。
- 同一入力・同一Skill package・同一生成promptでr6を1回実行したが、sanitized workspace内の合成Git baselineとsource revisionの関係がAgentへ伝わらず、AgentはQA分析前にblockedとなった。このattemptは品質所見の再現試験として有効でなく、再実行していない。
- r5の`execution-record.md`誤登録とtarget integrity不備はEvaluator側で検出されており、r5をPASS扱いしていない。再発防止としてtarget root / synthetic baselineの照合、未分類outputの非PASS化、Agent向けsource provenanceを追加した。
- Skill成果物の修正は行っていない。r6ではREV-001、REV-002、24時間境界を評価できず、Skill起因の再現性を確認できなかったためである。
- すべて開発用の検証である。共有workspaceの読取拒否、実効モデル、正式runner、独立Judgeは未検証のまま維持する。

## 評価条件と証拠

| 項目                      | r5                                                                        | r6                                                                                                |
| ------------------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Evaluator / Skill HEAD    | `32008149d6204523d2e9deaf09e88866627a7b0b`                                | 同一                                                                                              |
| Target source revision    | `84ce165493649550832731a60cf436f8ae29c56b`                                | 同一。sanitization前のsource checkoutは同SHA・clean                                               |
| Task SHA-256              | `sha256:a40343bce1d62d727c236cdc759d125c1b77f7375b7786d9af7e0a65bc938e98` | 同一                                                                                              |
| Generation prompt SHA-256 | `sha256:87d5537bb2847756848ee57bd252f139fe74aee7615e052bf9c731b8ef2f13d2` | 同一                                                                                              |
| Skill package fingerprint | `sha256:28162d13deecf08731ade613914be8b4c210c8003ddecd9a391dffe150cd7cea` | 同一                                                                                              |
| Agent設定                 | `gpt-6-luna / max / fork_turns=none` 指定                                 | 同じ値を指定                                                                                      |
| 実効モデル確認            | telemetryなし                                                             | collaboration toolから取得できず未確認                                                            |
| TargetのGit metadata      | local `.git`なし。Git discoveryが親Evaluator repositoryへ到達             | sanitized helperが合成1-commitを作成。HEAD=`47a90dcbc5fd90a5525fc635b533db6d52f4bbf3`、remoteなし |

r5の正本は`.agent-eval-runs/pr17-qts-dev-current-head-20261101-r5/evidence-index.md`と、その`evaluator-private/parent-validation.json`。今回のattemptは`.agent-eval-runs/pr17-qts-dev-repeat-r6-20261101/evidence-index.md`およびprivate parent validation、prompt、source/target manifest、Agent出力に保存した。

## r5の品質所見

### REV-001: TCN-005のblocked範囲

固定仕様の[`BR-CHECKOUT-003`](https://github.com/ryu-yoshikawa-pro-vision/qa-training-store/blob/84ce165493649550832731a60cf436f8ae29c56b/docs/spec/features/checkout-and-payment.md#L17-L19)は、TEST-SUCCESS、明確な失敗、processingの別経路を定義し、最終在庫不足時の具体tupleだけを未確定にしている。

r5の上流Question AnalysisもQ-001の影響を最終在庫不足へ限定している。一方、Test Condition DesignはTR-004、TR-005、TR-006を同じTCN-005にまとめた。`decision-003`は`final_inventory=insufficient`に対するAuthority不足で正しくunresolvedとなり、materialize helperはTCN-005全体をblockedにした。その結果、readyだった明確な拒否、processing、TEST-SUCCESSの条件もTCN-005配下ではCIを得なかった。

最初に確認できる過剰な影響範囲はTCN-005の工程分割である。runtime helperのblockedはその入力に対して正しい。test-condition-designの分割指示が不足している可能性はあるが、r5単独ではSkill欠陥と確定しない。

### REV-002: TC-016の成功期待

r5のTC-016はCart Version / priceが一致するTCN-004-CI02に対し、Confirm Order後のOrder・Payment作成とCheckout Completeを期待した。しかしTest Dataと操作にはLocal Mock Paymentの`TEST-SUCCESS`がない。固定仕様で成功状態を確定する条件はTEST-SUCCESSなので、記載された入力だけでは期待結果を導けない。

最初に見える不整合はTest Case Designの入力・期待結果の組合せである。上流CI02はCart / price gateを表しており、Payment successを付加しない。既存Skillの明示的テストデータ・期待結果契約もあるため、現時点ではAgent出力の不備として分類し、Skillの安定欠陥とは断定しない。

### 24時間境界の質問

r5のTest AnalysisとTCDは、Session開始から24時間ちょうどの比較演算子が未定義であると記録し、等値境界の合否は作らなかった。Question AnalysisのQ-001は最終在庫不足だけを扱っており、expiry境界を含まない。

Question Analysisの契約では未解決事項を影響に応じて分類し、回答があれば設計が変わるが現在の成果物は正当に作れる事項は`要確認`として継続できる。従って24時間等値はQ-001とは別の非blocking確認候補である。r5の質問表への未登録は所見として残すが、TCNが等値ケースを除外しており、追加attemptが準備段階で停止したため、Skill起因とは確定しない。

## Artifact indexとrouting

r5には必須8種類とQuestion Analysisの9正規成果物に加え、`qa-workflow / execution-record`が10件目のartifactとして登録された。固定scenarioはこのkindを許可せず、`validate_artifact_index()`は`unexpected_artifact_kind`を返した。Validatorとscenarioの許可kindは変更していない。

14 routing rowsの内訳は6 executed、3 incomplete、5 skippedだった。

- TCD、Test Case、Coverageの3 incompleteは、blocked materialization、TC-016の未根拠期待、traceability未解決を残しており、完了扱いしない判断として妥当。
- 5 skippedはlive UI inspection、test execution、E2E inspection / implementation / executionで、固定scenarioの分析・設計範囲外。scope外skipとして妥当。
- `qa-workflow`は成果物と最終runtimeが実行され、`can_complete=false`を返したため、工程statusのexecutedとworkflow未完了は両立する。
- `execution-record.md`は運用記録として保持すべきだが、QA成果物indexへ登録してはならない。正規のattempt実行情報はEvaluator側に保存する。

r6ではAgentが出力したindexのJSON構造自体は読めたが、親の固定scenario validatorは`needs_review`を返した。8 routingがすべてblockedで、workflow decision以外の必須7成果物が欠落していた。Agent側の簡易schema確認を評価PASSとは扱わない。

## Target integrity

r5の`target_workspace`にはlocal `.git`がなく、`git rev-parse`等が親のEvaluator repositoryを発見した。integrity判定はfalseとなり、r4 baselineと一致する1,121 source entryに対して追加された8個の`__pycache__`を差分として検出した。これらは`.gitignore`による隠蔽でも見逃されていない。Product Code、Test、規範仕様に変更はなかった。

r6は`prepare_sanitized_target()`が固定source SHAからtracked contentを抽出し、target内にremoteなしの合成1-commitを作成した。baseline manifest 1,121 entryはAgent終了後も一致し、pycacheは0件だった。`.qa-eval-input/task.md`は起動前からuntracked baseline fileとしてmanifestへ含めており、Agent後の変更ではない。runtime helperは一度も実行されていないため、bytecode抑制下でhelperを実行した評価ではない。

r6のtarget integrityは当時のhelperでunchangedだったが、helperはGit rootがtarget自身か、HEADが準備時の合成baseline SHAかを明示検証していなかった。また、合成Gitとsource revisionの違いをAgentへ伝えていなかったため、Agentが`git cat-file`でsource SHAを解決できないとして停止した。この試行はr5とAgent-visible Git条件が異なるため、同条件の品質比較にも使えない。

## 実施した修正

- `target_workspace.py`: target / output root symlink、symlink・非通常filesystem entryを拒否。全非output fileを走査し、Git rootがtargetと一致すること、準備時の合成HEAD、単一commit、remoteなしを検証する。
- `qa_training_store.py`: 実行時に準備時のsynthetic baseline SHAをintegrity validatorへ渡す。artifact manifestの未分類fileやunsafe symlinkがあれば、indexがpassでもattemptをneeds_reviewにする。
- `prompt_builder.py`と評価用`AGENTS.md`: 固定source revisionからsanitized filesを抽出したこと、local Gitがintegrity用synthetic baselineであることを明示する。Agentにsource SHAのGit object解決やfetchを要求しない。artifact-indexにはscenarioのQA成果物と必要なQuestion Analysisだけを登録し、実行記録・runtime記録はQA成果物にしない。
- フェーズ2Plan: source revisionとsynthetic baselineの区別、target root / baseline SHA / filesystem scan契約、execution evidenceとQA artifactの分離を明文化した。
- 回帰テスト: 固定sourceとsynthetic HEADの区別、親Git repository discovery拒否、HEAD不一致、tracked / untracked / ignored差分、symlink root/output/destination、非通常entry、未登録execution recordとoutput内のFIFOのnon-passを追加した。

QTS製品仕様、Product Code、既存Product Test、Judge fixture、artifact-indexの許可kind、Skill本体は変更していない。

これらの修正はr6 attemptの後に行ったため、r6のAgent成果物を修正後の条件で生成したとは扱わない。修正後のAgent再実行はしていない。したがって、既知の準備・評価記録の欠陥をテストで塞いだことは確認したが、REV-001、REV-002、質問漏れの再現性は引き続き未判定である。

## 検証と未達

- Agent evaluator suite: `python -B -m unittest discover -s scripts/skills/evals/agent/tests -p 'test_*.py' -v`で173件実行、2件skip、残り171件PASS。
- Focused tests: `test_target_workspace`と`test_qa_training_store`がPASS。target integrity、未登録成果物、FIFOを含む不正outputを検査した。
- Python構文検査は変更した5つのPython sourceをcompile-in-memoryで確認。`compileall`は不要な`__pycache__`生成を避けるため実行していない。
- Ruff: ローカル環境に`ruff` executable / Python moduleがなく、実行不可。CIで再確認する。
- dprint 0.55.2の変更文書checkと`git diff --check`はPASS。
- 現行helperでr6 targetを再確認し、target root、synthetic HEAD、1 commit、remoteなし、baseline manifestの一致を確認した。source checkoutも固定SHAでclean。結果は`.agent-eval-runs/pr17-qts-dev-repeat-r6-20261101/evaluator-private/postchange-helper-check.json`に別保存した。この事後確認はAgent実行時の元evidenceを置き換えない。
- 変更後にAgent評価は再実行していない。r6は旧promptで既にblockedとなり、同じ失敗を繰り返していない。
- r5のREV-001、REV-002、質問漏れは再現未確認のためSkill patchなし。
- QTS workflowは完了していない。r6は仕様分析を開始しておらず、runtime evidence、workflow runtime、traceabilityは未検証。
- Subagent起動時の指定値は`gpt-6-luna / max / fork_turns=none`。実効モデル/build telemetryとEvaluator情報の物理read-denialは確認できない。
- 正式runnerの認証refresh永続化、非協調process境界、Judge fixture 11件の承認、独立Judgeは未達のまま。今回の開発用attemptを正式結果へ読み替えない。

ローカルRuff実行環境にはRuff 0.16.8がなく、Ruff lint / formatは未実施。変更HEADのGitHub CIで検証する。
