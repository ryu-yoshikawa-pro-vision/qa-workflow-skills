# PR #17 QTSサブエージェント統合評価（第2段階）

## 結論

Codexホストのサブエージェント出力を、固定QTS targetへ取り込み、attempt別にcaptureし、既存のartifact-index検査とruntime証拠検査へ渡す開発用経路を追加した。2回の実Agent実行はどちらも固定promptを使用し、sanitized targetは固定source revisionと一致した合成baselineから変更されていない。

両attemptで公開artifact-indexの構造検査はvalidだった。一方、下流成果物とruntime証拠に未完了・未検証があり、固定artifact validatorと総合結果は両方`needs_review`となった。QA workflowの意味的完了、production verifier replay、Judge評価は実施していない。これは正式な独立評価やQA workflowの合格を示すものではない。

## 固定条件と実行条件

| 項目                           | 値                                                                        |
| ------------------------------ | ------------------------------------------------------------------------- |
| PR開始HEAD / Skill revision    | `296e64919a61617243b22f56b3bb3edd16693244`                                |
| base / branch                  | `main` / `feat/agent-eval-runner`                                         |
| QTS source revision            | `84ce165493649550832731a60cf436f8ae29c56b`                                |
| Scenario                       | `qa-training-store-checkout-payment-web-v1`                               |
| Scenario fingerprint           | `sha256:b9aedc1b00bc2bcdf3a91735b008f9e89ecb403482f4ca84a20b4648180a8a5c` |
| Generation prompt fingerprint  | `sha256:80457aa75bc411dd45145055378ba777fec5b3fcc7b6e3bbbf48e41680ea6541` |
| Run ID                         | `d3ab14c200964233b76acbb26ef7a676`                                        |
| 要求設定                       | `gpt-6-luna` / `max` / `fork_turns=none`                                  |
| 実効model/build、tool trace    | 未検証                                                                    |
| 物理的なEvaluator-only読取拒否 | 未検証。共有workspaceのため保証しない                                     |

固定source checkoutのHEAD・clean状態、評価対象Skill package、sanitized targetのGit root・HEAD・remoteなしの合成baseline、必要な仕様ファイル、公開artifact-index契約、Python bytecode抑止、target integrityを実行前に確認した。Agent向けpackageにexpected、rubric、grader、Judge fixture、Reference、他attemptの生成物は配置しなかった。Agent-visibleの一時targetだけでは物理的アクセス拒否を証明しない。

AgentはCodexホストのサブエージェント機能で逐次起動した。起動要求値は両attemptで明示・記録したが、実効model/buildや完全なtool履歴を裏付けるtelemetryはない。開始時刻はattempt用task fileがmaterializeされた時刻を下限として記録し、正確なlaunch時刻は未検証とした。

## attempt結果

| attempt                            | Agent結果                                   | QA artifacts / routing                                                                                   | 公開index         | 固定index / 総合                |
| ---------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------- |
| `d7760de6d12d4c78b45c359017b0eea6` | host execution `completed`、prompt hash一致 | 9 / 9。routingは`executed` 3、`incomplete` 6。`question-analysis`を含む                                  | valid、issuesなし | `needs_review` / `needs_review` |
| `0ddf91f4b33046588a42eee224d40612` | host execution `completed`、prompt hash一致 | 8 / 9。routingは`executed` 4、`skipped` 1、`incomplete` 3、`blocked` 1。`question-analysis`はAgentがskip | valid、issuesなし | `needs_review` / `needs_review` |

両attemptとも対象targetの変更はなく、Git root・synthetic baseline HEADが準備時と一致し、remoteはなかった。秘密情報に見えるpathは検出されなかった。output captureはattempt 1が17 files / 111,514 bytesで`captured`、attempt 2が23 files / 417,626 bytesで`captured_needs_review`だった。後者では`.runtime-work/`の8ファイルが正規QA成果物にも既知のruntime-evidence分類にも該当せず、許可外・未登録として保存された。分類契約を緩めていない。

### runtime evidenceと未完了判断

- attempt 1では`test-analysis`、`test-requirement-design`、`test-condition-design`、`test-case-design`、`coverage-analysis`、`qa-workflow`の必須runtime captureが不足した。Question AnalysisのID helperとspec-analysisのAuthority Entity処理にはrequest/resultはあったが、対応するinvocation recordがなく、関連ファイルは`runtime_file_without_invocation`として未検証になった。
- attempt 2では`test-analysis`と`test-requirement-design`の`verify-001` invocationを保存したが、同一attempt内で同じinvocation IDを使っていた。QTS統合Planはinvocation IDをattempt内で一意とし、retryにも別IDを要求する。Evaluatorは重複を拒否した。spec-analysis、test-condition-design、test-case-design、coverage-analysis、qa-workflowにも必要なcaptureが不足した。
- attempt 2のAgentはTest Condition Designを`incomplete`、Test Case DesignをcurrentなTCN/CI Entity不足で`blocked`、Coverage Analysisと`qa-workflow`をruntime未完了として記録した。これらをPASSやcompleteへ変えていない。
- attempt 2はQuestion Analysisを`skipped`と記録した。公開・固定indexは構造上の契約に従って処理したが、そのskip理由の意味評価は未実施であり、採点済みとは扱わない。
- 両attemptで`workflow_completion`は`not_semantically_verified`、`can_complete` claimはなし。意味的QA品質・traceabilityの有効性はJudge未実施のため未判定。

runtime invocation ID重複と`.runtime-work`の未登録はattempt 2で実際に検出した入力・出力契約違反として保存した。Evaluation recordはinvocation failureを一般的な`AgentEvalError`として記録するため、個別原因は保存済みinvocation一覧の一意性を照合して特定した。Evaluatorの検査を弱めていない。

## 実装

- `qts_subagent_eval.py`にQTS専用の`prepare`、`record-execution`、`capture`、`evaluate`を追加した。単一Eval Input用の`subagent_eval.py`は変更していない。
- 既存の`prepare_sanitized_target()`、Skill workspace/package manifest、`build_qa_training_store_generation_prompt()`、公開artifact-index checker、`qa_training_store.validate_artifact_index()` / `build_artifact_manifest()`、`common_runtime_checks`のruntime request/result検査、target integrity検査を利用する。
- `common.py`にsymlinkを追わない、hardlinkを拒否する、sizeとread前後のidentityを検査するregular-file readerを追加し、QTS保存copyにも適用した。
- Stage 1の`subagent_eval._read_regular_bytes()`を同じ共通readerへ委譲し、単一Eval Inputのhandoffを維持したままfile-safety実装を共有した。
- 実runで`result.json`のattempt row更新が反映されないバグを発見した。`_attempt_paths()`が別にloadしたrun objectのrowを返し、そのrowを元のrunへwriteしていなかった。既にload済みのrunを渡すように修正し、execution・capture・evaluation statusとfingerprintがrun indexへ保存される回帰テストを追加した。
- このindex修正は2回の生成・採点後に行った。元のrun indexを`evaluator-private/run-index-before-reconciliation.json`へ保全し、attempt-local `attempt.json`、`capture.json`、`evaluation.json`のみからrun indexを再構成した。元・再構成後のhashと導出元hashを`run-index-reconciliation.json`に残した。品質結果は変更せず、両attemptのstatusは`needs_review`である。
- 2回の実Agent評価は、`qts_subagent_eval.py`の事前修正source fingerprint `sha256:1c77d3018530a1953e5bc3c0474fc7ac01f1193f56b85de4a4c7a0e1460dc491`で実施した。今回の修正後source fingerprintは`sha256:b8eb3e6f0e4142ed73853544656bee365061534544c008da03e92e8d73466bc6`。差分はrun-level statusの保存とその回帰テストに限定し、artifact検査・品質判定は変更していない。最終sourceでの実Agent再実行はしていない。

## 保存証拠

Git管理外の証拠root：

`.agent-eval-runs/pr17-qts-subagent-stage2-20261103-03/`

各`attempts/<attempt-id>/evaluator-private/`にprompt、attempt条件、execution record、capture manifest、captured outputs、artifact manifest、runtime検査、評価結果を保存した。run-level `result.json`はattempt ID、requested settings、status、evidence fingerprintを一覧する。準備コード変更中に作成した次のsuperseded evidenceも削除していない。

- `pr17-qts-subagent-stage2-20261103-01/`：Evaluator変更のためAgent起動前にsuperseded。
- `pr17-qts-subagent-stage2-20261103-02/`：一度、準備promptと異なるhandoffが始まり`invalid_handoff_interrupted`として保持。その後の未実行attemptもコード変更でsuperseded。いずれも品質比較へ含めていない。

これらは最終の2有効attemptとは別の準備・handoff失敗記録である。最終run 03内の2 attemptは両方とも同一prompt fingerprintで完了し、都合の悪い品質結果を除外していない。

## 検証

- Agent evaluation unit tests：213 tests passed、2 skipped（full suite。WSL2固定runtime integrationは専用環境変数がないためskip）。run-level state persistenceの修正を含む。
- repository contract tests：4 passed。
- `compileall`：成功。
- dprint check（READMEと変更Pythonファイル）：成功。
- `git diff --check`：成功。
- Ruff：ローカルに未導入（`ruff: command not found`）。`4ee7c78`で未使用importを検出し、`3646f91`で削除した。続くCIでは3ファイルのformat、さらに`2b8f485`ではQTS testの1行のformatを指摘したため、各CIのRuff 0.16.8差分を反映した。ローカルpip installはネットワークDNS制約で失敗し、Ruff自体の再実行はCI待ち。
- 作業開始時のPR HEAD `296e64919a61617243b22f56b3bb3edd16693244`のGitHub Actions 5 workflowはすべて成功。`4ee7c78`は未使用import、`3646f91`と`2b8f485`はRuff formatでCode Qualityが失敗した。次のfollow-up commit後に5 workflowの最終状態を確認する。

## 未検証・次工程

- Artifact indexの構造・参照とfile presenceは機械検査済みだが、QA成果物の意味的な正しさ、仕様根拠、Question Analysisのskip妥当性は未評価。
- Skill-local `verify`の一部request/resultは保存したが、全必要skillのruntime evidence captureは揃っていない。`common_runtime_checks`のrequest/result hash照合は既存helperを使うが、欠落・重複を含むため全runtimeを有効とは扱わない。
- Docker不要の独立production verifier replay、Docker production verifier、独立Judge、Judge fixture承認、`improve.py`ライブ改善は未実施。
- requested model設定は保存済みだが、実効model/build、完全なtool trace、OSレベルのEvaluator-only読取拒否は未検証。
- ここまでの成果はStage 2の開発用実行・取込・機械検査経路の実動作検証であり、正式な独立統合評価やworkflow品質合格ではない。
