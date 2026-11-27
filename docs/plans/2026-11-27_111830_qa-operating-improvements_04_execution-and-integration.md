# 実行安全・証跡・報告・外部接続の改修

## 目的・対象範囲

OPS-06・07・08・10・16・18。独立したQA活動の並行実行を不要な案件全体の排他で止めず、実際に競合する操作だけ安全に制御する。実行前条件、実測結果、原因分析、欠陥候補、統合報告を既存ownerで接続し、結果の改変や誤完了を防ぐ。01〜03の保存・承認・完了契約に従う。対象製品の修正、無認可の実環境操作、未指定の外部起動サービスは対象外。

## 現状と維持する契約

- `qa-workflow/scripts/artifact_graph.py` の `claim_mutable_operation`（L3080〜）、`read_mutable_operation_claim`（L3170〜）、`recover_claim`（L3228〜）、`reserve_shared_resource`（L3252〜）、`release_shared_resource`（L3292〜）には未接続経路がある。`recover_claim` は条件が揃っても `claim_release_provider_not_connected`、予約・解放も実provider未接続の場合blockする。能力フラグだけで実認可・予約を証明しない。
- `qa-workflow/references/guidance.md` と [#22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md) の同一案件並列制約は現行契約である。改修・検証が済むまで回避しない。
- `test-execution`、E2E、testware実行、探索、使用性観測は別の実行ownerを持つ。E2E固有報告と計画母集団に基づく統合報告は別目的。元結果、初回FAIL、retry、cleanup、権限・実行上限、実コードの変更権限を維持する。
- `testware-implementation/scripts/publish_git.py`、`snapshot_guard.py` はコード変更・隔離・許可差分・条件付きGit反映を扱う。通常QA文書の保存簡素化の対象ではない。

## 実装1 競合単位と並行実行

`qa-workflow/SKILL.md`、`references/guidance.md`、`assets/workflow-state-template.md`、上記artifact_graph関数と実行ownerのpreflightを以下に揃える。

<!-- dprint-ignore -->
| 作業条件 | 必要な処理 |
| --- | --- |
| 読取専用・独立分析 | 共有資源予約・claim不要。対象と情報源の許可だけ確認 |
| 異なるscopeの成果物を分離した作業先へ書込 | 案件全体の排他不要。各保存先・ID・依存の混線を防止 |
| 同一正本の共有更新 | 02の必要な条件付き保存・一意性を利用。予約で保存競合を代替しない |
| 独立ブラウザ・独立データ・独立実行環境 | 実際に隔離されていることをpreflightで確認。案件全体の予約不要 |
| 同一ユーザー・共有データ・外部サービスの状態変更 | 実ownerが必要とする隔離、冪等開始、予約、条件付き解放、上限・cleanupを確認 |
| 状態変更結果が不明 | 元実行ownerの状態・結果・cleanupを取得。二重実行可能性が解消されるまで該当操作を再試行しない |

実装手順:

1. `test-execution` / `e2e-test-execution` / `testware-execution` / `exploratory-testing` / `usability-inspection` / `test-target-inspection` / `defect-management` のSKILL.md、reference、実行入口からclaim・reservationの呼出しを確認する。操作・対象・実際に共有する資源に絞って必要性を判定する。同一案件だけを理由に停止する記述とfixtureを改める。隔離の根拠がなく共有操作が必要な場合は従来のblockを維持する。
2. ownerが既に冪等開始・実開始証拠・cleanupを持つ場合はその機構を使い、二重の汎用claimを作らない。`claim_mutable_operation` は必要な副作用開始を守る未接続経路に限定して利用する。`read_mutable_operation_claim` のcurrentは開始許可を意味しない。旧claimが存在する場合は履歴として保持し、実ownerの状態を確認するまで再実行しない。
3. `recover_claim` / `reserve_shared_resource` / `release_shared_resource` は実際の利用先が保証できる既存owner/実行環境の条件付き操作を用いる。未選定の共有providerに新しい汎用実装を作らない。実用経路で必要な場合は実ownerの実結果・認可・revisionに結び付けた接続を実装し、競合・失敗・再取得を試験する。使用しない経路は利用者への設定要求を除き、呼出しのない管理専用処理を削除する。旧予約ファイルやDBを自動削除・移行しない。
4. 副作用の重複防止は対象操作を基準にする。#40の `semantic_handoff_key` と既存ownerの実ref・lookup・一意性・readbackを活用する。通常の対話質問提示にはhandoff claimを要求しない。別ref・異なるworkflowの同じ外部Issue/質問/Knowledge作成で実ownerの一意性が証明できない場合は、実ownerの反映があるか調査し、必要条件が不足するcreateをblockする。fixtureやハッシュの一致だけで跨ownerの一意性を保証しない。
5. [#22マージ判断](../implementation/pr22/merge-decision-2026-11-14.md)の過去記録は上書きしない。改修された現行の同一案件並列条件は新しい担当契約へ明記し、現行文書から旧一律制約を除く。過去対象外の実環境は別途必要な認可を得て検証する。

### 呼出し経路ごとの扱い

- test-target-inspection、e2e-test-inspection、読取だけのusability-inspection/探索、分析・レビューは汎用claim/reservationを呼ばない。実データ変更を伴う探索・観測は実行ownerの操作前条件へ進む。
- test-execution は個別TCの実操作・attempt・副作用上限・cleanupを既存ownerで確認し、共有ユーザー/データへの操作でのみ実予約を要求する。E2E/testwareはrunner固有の実開始、隔離、manifest、cleanupを使用し、同じ実行を別の汎用claimで二重管理しない。
- defect-management の外部Issue、A/Bからの質問・Knowledge・欠陥の永続handoffは実ownerの一意性・pending intent・readbackを利用する。対話質問やローカル候補のみなら外部claim不要。実ownerの保証がない外部createは対象だけ停止する。
- artifact_graph.py の claim_mutable_operation/read_mutable_operation_claim は実副作用で既存ownerに冪等開始がない経路だけ残す。recover_claim/reserve_shared_resource/release_shared_resource は既存の実owner/環境が安全に実行できる場合だけ接続し、実接続のない能力フラグを認可・予約成功へ読み替えない。呼出し元がないことを確認できた管理専用CLI/設定は除去する。過去のclaim/予約は状態不明のまま勝手に解除・削除しない。

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

実運用の共有writer・外部ownerの横断一意性は#40のローカルfixtureで実証済みではない。必要な共有保存・外部handoffの実接続で、実行結果不明後のlookup、同じsemantic handoff keyの再送、重複生成防止、権限不足時の局所停止を確認する。対象の接続・権限がなければ未検証として記録する（05のAT-10/11/14）。不要な接続を評価のためだけに構築しない。

## 実装4 WCAG closureガイダンスと直接利用（OPS-08・09・14）

現行 `qa-workflow/references/guidance.md` L276〜278には、`finalize-wcag-report` がcurrent Machine Runtime rowを独立取得せずcaller metadataに依存する旧記述がある。`workflow_runtime.py` L245〜の `_execute_and_finalize_wcag_report`、`_wcag_state_operation`、`_runtime_metadata`、`_invoke_local_runtime`、`artifact_graph.py` のSQLite state/closure更新と `wcag-conformance-evaluation/scripts/wcag_runtime.py` のclose_report経路を照合し、実際の正規owner内部実行経路へ記述を置換する。

既存の偽candidate/metadata拒否、current rowの独立取得、canonical Planの束縛、CAS conflict、履歴欠損、closure不完全、別connectionからのreadbackのテストを確認し、文書と実装を一致させる。文書修正が目的だが、テストが示す具体的な未解決不具合があれば必要な修正を行う。特権DB writer、複数host、実運用の本人性や意味判断まで保証するとは記載しない。WCAGの正式評価契約を汎用完了の簡素化で弱めない。

正式WCAGの _current_project_context と _wcag_state_operation、_execute_and_finalize_wcag_report、_runtime_metadata、artifact_graph.py の workflow_state_context_from_project_context と評価登録/read/finalizeの入力を同期する。既存Context経路はそのまま維持し、新規直接経路は明示 workflow_state_root（未指定時01の許可済み既定root）と実評価対象・source refs・環境・scopeを受ける。Context有無の判別を明示し、ContextなしではContext用ref/revision/fingerprintを架空生成しない。新規直接評価のsource bindingは実rootの正規化された絶対pathとworkflow_ref、実source refs・revisionを既存canonical JSON/hashで束縛し、登録・観測・read・finalizeで同じbindingを独立に解決・照合する。既存評価のContext fingerprint契約は当時の履歴として維持する。必要な根拠・権限・実rootが不明なら正式closureのみ停止する。旧Contextあり/なし、別root、別workflow、実source改版、改変候補、CAS競合、過去revision、独立readbackを既存WCAGの回帰へ追加する。

## 実装5 外部起動・CI入力/結果受渡し（OPS-10）

`qa-workflow/scripts/ci_handoff.py` の `verify`、source ref/build・差分path・成果物ref/hashesの検証、関連 `test_ci_handoff.py` を利用する。直接依頼と外部起動は同じQA意味契約で扱う。指定されたrepository・PR・branch・commit・外部仕様revisionはQA情報源として分析可能。成果物のGit管理や案件選択は外部責務。

- 直接依頼では指定情報源と必要な対象・成果物を使う。CI起動では呼出し側が同等の情報源/版/対象/権限/必要な結果先を供給する。新たな共通設定schemaや監視サービスは作らない。
- 既存ci_handoff入力でsource・差分・必要成果物の確認ができる場合は再利用する。sample CIの分類・列挙対象を全案件共通の要件にしない。未分類差分・不足source・未取得を0件や成功扱いしない。
- 実CI/release/外部Issue連携は利用者が必要とする接続だけ実装・受入する。接続先・実行/外部送信許可が未確定なら該当接続を未設定/blockedとし、直接利用を妨げない。実際に必要な接続の未達は全体完了時に明示する。

## 検証・完了条件

- `test_qa_operation_claim.py`、`test_pr24_artifact_store.py`、`test_context_artifact_store.py`、`test_context_workflow_state.py`、`test_ci_handoff.py`、`test_cross_owner_selection_to_inspection.py`、`test_cross_owner_results_to_reporting.py`、`test_cross_owner_exploration_to_defect.py`、`test_pr32_defect_management.py`、`test_pr32_test_reporting.py`、`test_testware_regression_handoff.py`、`test_workflow_runtime.py`、`test_sqlite_workflow_history.py`、`test_runtime_workflow_integration.py` を関連変更ごとに個別実行する。WCAG、runner、E2E、直接TCの既存テストは対象Skillの評価資産とruntime全suiteから特定して実行する。
- AT-10/11/12/15/16/17/18/20/21/25: 独立作業、同一正本更新、共有データ操作、結果不明、開始前中断、cleanup失敗、権限不明、未実行・FAIL・retry、母集団漏れ、部分報告、証跡保護を対比する。
- 許可された環境で、既存テスト直接実行、E2E、非E2E、Regression/Exploration、欠陥候補、統合報告を元の依頼範囲に応じて通す（05）。実接続が必要な場合はその経路も確認する。既存実行安全とrawの追跡を維持しながら不要な案件全体の停止・重複確認が解消され、WCAG文書とコードが一致した時点で完了。
