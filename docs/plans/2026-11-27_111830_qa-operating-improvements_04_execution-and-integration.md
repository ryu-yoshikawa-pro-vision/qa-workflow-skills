# 実行安全・証跡・報告・外部接続の改修

## 目的・対象範囲

OPS-06・07・08・10・16・18。独立したQA活動の並行実行を不要な案件全体の排他で止めず、実際に競合する操作だけ安全に制御する。実行前条件、実測結果、原因分析、欠陥候補、統合報告を既存ownerで接続し、結果の改変や誤完了を防ぐ。01〜03の保存・承認・完了契約に従う。対象製品の修正、無認可の実環境操作、未指定の外部起動サービスは対象外。

## 現状と維持する契約

- `qa-workflow/scripts/artifact_graph.py` の `claim_mutable_operation`（L3080〜）、`read_mutable_operation_claim`（L3170〜）、`recover_claim`（L3228〜）、`reserve_shared_resource`（L3252〜）、`release_shared_resource`（L3292〜）には未接続経路がある。`recover_claim` は条件が揃っても `claim_release_provider_not_connected`、予約・解放も実provider未接続の場合blockする。能力フラグだけで実認可・予約を証明しない。
- `qa-workflow/references/guidance.md` と [#22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md) の同一案件並列制約は現行契約である。改修・検証が済むまで回避しない。
- `test-execution`、E2E、testware実行、探索、使用性観測は別の実行ownerを持つ。E2E固有報告と計画母集団に基づく統合報告は別目的。元結果、初回FAIL、retry、cleanup、権限・実行上限、実コードの変更権限を維持する。
- `testware-implementation/scripts/publish_git.py`、`snapshot_guard.py` はコード変更・隔離・許可差分・条件付きGit反映を扱う。通常QA文書の保存簡素化の対象ではない。

## 実装1 競合単位と並行実行

同一案件だけで並行実行を止めない。読取・独立分析・分離済み成果物にclaimや予約不要。同一正本は担当writerを一つにし、別ファイル・worktree・scopeへ分離して必要な結果を統合する。実際に共有する環境、ユーザー、データ、外部サービス、reset、通知は操作の影響を確認し、隔離または既存環境の制御を使用する。

artifact_graph.pyのclaim_mutable_operation/read_mutable_operation_claim/recover_claim/reserve_shared_resource/release_shared_resourceと各ownerのpreflightを改修する。reserve/releaseは現在未接続providerを理由にblockする経路であり、汎用予約基盤を新設しない。既存ownerの実開始・結果・cleanup・必要な冪等性を使い、不要なclaim/reservationの呼出し・設定・テストを除く。結果不明の副作用に必要な記録を保全し、旧claim/予約を勝手に解除しない。

testware-implementationのpublish_git/snapshot_guardは明示された共有先への反映時だけ必要なGit条件を使用する。通常worktree編集に予約不要。testware-executionのcontract.py/runner.pyは独立したローカル実行を不要な予約で止めない。checkout・コマンド・隔離・副作用上限・cleanupを維持する。runner.executeのnative_provider_authorization_required/side_effect_limits_unenforceableは実際の外部副作用・共有資源・上限を保証できない操作に対して維持し、未対応操作を解放するproviderを新設しない。独立実行と拒否条件をリポジトリ内テストで対比する。

defect-managementの外部IssueやA/Bの外部handoffは実際の利用者許可・サービス権限・対象・必要承認を確認し、既存結果を調べて反映する。結果不明の副作用を再実行しない。通常質問・ローカル候補/Knowledge保存に外部claim・認証サービス不要。実際の同時外部操作に重複防止が必要なら既存ownerの一意性または担当分離を使用する。保証できない危険な操作だけ停止する。過去の#22判断・#40検証記録は当時の記録として保持する。

## 実装2 実行から報告までの横断処理

対象Skillは `e2e-test-inspection`、`e2e-test-implementation`、`e2e-test-execution`、`e2e-test-result-analysis`、`e2e-test-reporting`、`test-execution`、`testware-implementation`、`testware-execution`、`regression-testing`、`exploratory-testing`、`defect-management`、`test-reporting`、`test-evaluation`。対応する既存reference・template・runtime/runnerを修正する。

<!-- dprint-ignore -->
| 処理 | 実装上の変更・維持 |
| --- | --- |
| inspection→実装/実行 | 実効設定、対象repo/build、環境・データ、実行許可の確認結果をcurrentであれば再利用。実開始直前に変わり得る条件だけ再確認し、不要な同一調査を削減 |
| 詳細TCの直接実行 | 実行前YAMLの固定、1件ずつのTC準備・実操作・後処理、共有副作用上限・cleanupを維持。最終Markdownに実行前YAMLを保持 |
| E2E・非E2E実行 | 既存runner・reporter・`testware-execution/scripts/contract.py` / `runner.py`を使用。元run、primary結果、attempt、raw、診断、環境/buildを区別。既存runnerの保護領域と実行制約を維持 |
| retry・修正確認 | 初回FAILとattemptを不変にし、再実行後の結果と原因・修正確認を追跡する。修正確認と別目的Regressionを区別 |
| Regression/Exploration | `regression_runtime.py`、`exploratory_runtime.py` のBaseline、Activity、Run、Charter、Session、Findingを維持。元実行ownerの結果を参照し、重複したraw・集計正本を作らない |
| 欠陥候補 | `defect_runtime.py` を利用。観測と期待の差、再現条件、根拠、仮説・確認済み欠陥、影響を分ける。Issue更新は許可済み実経路だけ。未設定なら候補・修正確認依頼まで |
| 報告 | E2E固有報告は対象E2E結果を報告。`test-reporting/scripts/reporting_runtime.py` は計画母集団と実取得の完全性に照らす統合報告。欠落sourceを0件扱いしない。初回結果を修正しない |
| 終了・評価 | 合否、取得完全性、終了基準、必要cleanup、workflow完了、リリース判断を分ける。計画なし/母集団不明では全体率・終了判定undetermined。FAILを含む必要工程完了は可能 |

実際に同じ値を複数成果物へ保存している場合は、独立した正式snapshot・過去結果の再現など保存理由があるか確認し、不要な複製は参照へ置換する。必要な元結果・実行証拠を削らない。テストの実行基盤・既存Playwright選択順は今回の改善で勝手に変更しない。利用者の明示したCLI等の条件がある場合は既存安全契約と両立する形で扱う。

### 引継ぎ時と実行直前の確認

inspectionの成果物から対象build、実効設定、locator/fixture、選定ID、検証可能性、必要環境・データを再利用する。E2Eは現在checkout・runner設定・対象suite・認証/データ隔離を開始直前に確認する。非E2Eはtestwareの許可checkout・manifest・対象test・保護領域・timeout/cleanupを確認する。直接TCはTC ID/期待根拠と実行前YAMLを再利用し実環境・状態・権限・操作上限を確認する。Regressionはbaseline/membership/Run予定の選択と元結果ref、ExplorationはCharter/Session/Finding/観測条件を再利用し、実対象・時点・操作条件を再確認する。build・対象・権限・環境・データが変わったら影響する実行範囲だけ見直す。全ownerで実開始していない結果をPASS/FAILにせず、必要cleanupが不明なら実行完了としない。統合報告には計画母集団と取得・実行・判定状態を引継ぎ、別目的の集計を混ぜない。

## 実装3 証跡保護・結果不明・cleanup

01の保護領域を実行経路へ接続する。実行前条件、実操作上限、環境、raw保存の許可と期限を既知条件から確認する。未知の危険な操作を試して確認しない。認証token、Cookie、秘密の実値、機密DOM/raw等を通常QA成果物、フォーム、公開ログへ入れない。安全な要約または許可refに限定し、rawが取得できない場合は証拠不足を明示する。root逸脱・symlink・保護領域外一時script生成を既存安全契約と実行環境で拒否する。

cleanupの成功は実際の対象状態から確認する。失敗・結果不明は該当実行範囲の制約として残す。予定母集団、run、attempt、必要履歴をcleanupで消さない。結果不明の再実行では、副作用が発生した可能性を上限から差し引く既存test-executionの契約を維持する。

共有writerや外部ownerの実運用受入は対象外。既存mock・fixture・一時ディレクトリで独立作業、実際の共有条件、結果不明後のlookup、必要なsemantic handoff keyの再送、重複防止、権限不足時の局所停止を検証する（AT-10/11/14）。実サービスの認可・実運用を検証済みとはしない。

## 実装4 WCAG正式評価の保存・closure（OPS-08・09・14）

現行guidance L276〜278のcaller metadata依存という説明はowner内部実行と不一致。現行契約を正しく説明し、正式評価のSQLite必須条件を解消する。workflow_runtime.pyの_current_project_context、_wcag_state_operation、_execute_and_finalize_wcag_report、_runtime_metadata、_invoke_local_runtime、artifact_graph.pyの評価登録/読取/closure更新とworkflow_state_context_from_project_context、wcag_runtime.pyのclose-reportと_evaluation_statement_with_saved_report、関連renderer・テストを同期する。

許可済み評価ディレクトリにcanonical Plan、実source refs・版、評価対象/環境/scope、sample/variation/process、criterion結果、観測handoffと必要証拠を既存機械契約のJSONで保存する。Contextは有効情報がある場合だけ使用し、なければ評価入力を直接受け取る。未指定rootは01。架空Context ref/revisionを生成しない。

正式報告では実保存Planと現在の評価結果を既存WCAG runtime close-reportへ渡し、実runtime結果と評価ref、評価対象の版、WCAG version/level、criterion ref集合、必要な評価工程・証拠・closureを対応付けてJSON保存する。正式報告Markdownは既存renderer。二段階CAS・別connection・全状態revisionを廃止する。不完全な評価で以前の正式報告を上書きしない。Evaluation Statementでは保存Plan・評価結果・実runtime出力・closureと要求する版/level/scope/criterion集合を照合し、現在の正式評価に合致しなければ生成しない。caller自己申告・偽metadataを証拠にしない。全更新履歴や別DBは不要。

WCAG-EM工程、sample/variation/process、ランダム選択の実結果、現在性、観測probe、HMACの機密locator保護、正式適合主張・EARLの意味は維持する。Contextあり/なし、別評価/別root、source改版、criterion集合不一致、closure不完全、偽候補、実runtime結果不一致、Statement誤生成、保存失敗・再開を既存fixtureで回帰する。SQLite固有テストは削除し、評価結果・証拠の検証へ置換する。

## 実装5 外部起動・CI入力/結果受渡し（OPS-10）

`qa-workflow/scripts/ci_handoff.py` の `verify`、source ref/build・差分path・成果物ref/hashesの検証、関連 `test_ci_handoff.py` を利用する。直接依頼と外部起動は同じQA意味契約で扱う。指定されたrepository・PR・branch・commit・外部仕様revisionはQA情報源として分析可能。成果物のGit管理や案件選択は外部責務。

- 直接依頼では指定情報源と必要な対象・成果物を使う。CI起動では呼出し側が同等の情報源/版/対象/権限/必要な結果先を供給する。新たな共通設定schemaや監視サービスは作らない。
- 既存ci_handoff入力でsource・差分・必要成果物の確認ができる場合は再利用する。sample CIの分類・列挙対象を全案件共通の要件にしない。未分類差分・不足source・未取得を0件や成功扱いしない。
- 実CI/release/外部Issueサービスの接続・運用受入は対象外。リポジトリ内のci_handoff、既存mock/fixtureで必要な入出力、権限・結果不明・未接続時の扱いを検証する。未対応接続は作らず直接利用を妨げない。

## 検証・完了条件

- `test_qa_operation_claim.py`、`test_context_artifact_store.py`、`test_context_workflow_state.py`、`test_ci_handoff.py`、`test_cross_owner_selection_to_inspection.py`、`test_cross_owner_results_to_reporting.py`、`test_cross_owner_exploration_to_defect.py`、`test_pr32_defect_management.py`、`test_pr32_test_reporting.py`、`test_testware_regression_handoff.py`、`test_workflow_runtime.py`、`test_runtime_workflow_integration.py` を関連変更ごとに個別実行する。WCAG、runner、E2E、直接TCの既存テストは対象Skillの評価資産とruntime全suiteから特定して実行する。
- AT-10/11/12/15/16/17/18/20/21/25: 独立作業、同一正本更新、共有データ操作、結果不明、開始前中断、cleanup失敗、権限不明、未実行・FAIL・retry、母集団漏れ、部分報告、証跡保護を対比する。
- リポジトリ内のテスト・fixture・mockで直接TC、E2E、非E2E、Regression/Exploration、欠陥候補、統合報告の連携を検証する（05）。実運用接続は要求しない。既存実行安全・raw追跡、独立作業の並行実行、WCAG正式評価の文書・コード整合を完了条件とする。
