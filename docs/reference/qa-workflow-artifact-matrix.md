# Skill別成果物・保存・利用者対応マトリクス

> 本文は現行実装の利用条件。2026-11-27合意の通常Markdown/JSON保存、SQLite・CAS・専用管理の削減は[実装Plan](../plans/2026-11-27_111830_qa-operating-improvements_00_index.md)で定める。実装改修までは現行の制約が有効。

[共通運用契約](qa-workflow-operating-contract.md)の別表。各Skillの正本・成果物、保存条件・形式・利用者対応を示す。成果物名は論理名。「指定先・担当形式」は、保存先・ファイル名を担当契約と利用者の指定から解決することを示し、固定パスやファイル名を一律に要求しない。具体的な形式・パスが定められる場合はその契約に従う。共通の保存対象・保存タイミング・承認・引継ぎは共通運用契約を参照する。現行Skill・Runtimeの契約に基づく一覧であり、保存機能・外部接続の実証を意味しない。

## Skill別

<!-- dprint-ignore -->
| Skill | 開始・更新 | 正本・成果物 | 保存・引継ぎタイミング / 場所 | 利用者の対応 | 保存形式・パス |
| --- | --- | --- | --- | --- | --- |
| [qa-workflow](../../skills/qa-workflow/SKILL.md) | 開始、工程移行、中断、再開、完了 | state、input revision、baseline | 開始・再開、質問前、工程引継ぎ、必要な操作前、実行後、完了時。state root・指定成果物先 | 目的・scope・成果物、必要時判断 | state root内の `<uuid>.json`、`claims/<digest>.json`、`artifacts/<uuid>/qa-workflow/<digest>.md`、対応SQLiteはworkflow-state.sqlite3。input-revisions.jsonは指定保存先 |
| [project-context](../../skills/project-context/SKILL.md) | 初回、設定・配置変更 | Context、DEC/ASM（ownerの場合）、配置参照 | 必要な合意・更新後、既存正本/指定先 | 保存先・編集範囲・権限合意 | 既存正本ref/path。docs/PROJECT_CONTEXT.md等は例 |
| [feature-analysis](../../skills/feature-analysis/SKILL.md) | 初回、PR/merge/release/改版 | 機能ID、機能台帳、source inventory、差分・履歴 | 分類検証後、feature root | source・基準ref・必要な除外承認 | qa.feature_artifact_root、担当契約のprovider・形式 |
| [spec-analysis](../../skills/spec-analysis/SKILL.md) | 仕様分析、変更、回答後 | Authority、US/UC/Behavior/AC、UNKNOWN、業務ルール | 分析・回答反映後、指定先またはui-target-v1 | 仕様回答・DEC/ASM承認 | 指定先・担当形式。ui-target-v1利用時は専用構造 |
| [ui-target-analysis](../../skills/ui-target-analysis/SKILL.md) | UI分析、変更、人間編集 | UI構造、操作、状態、遷移、編集差分 | 検証後既存materialize writer、package root | 資料、任意編集、必要承認 | 指定package root、ui-target-v1内部構造 |
| [question-analysis](../../skills/question-analysis/SKILL.md) | 任意工程の不明点、回答後 | Q ID、UNK、分類、履歴、再開先 | 質問前・回答反映後、指定先 | 必須回答・決定・仮定承認 | 指定先・担当形式（質問一覧・履歴） |
| [agent-answer-form](../../skills/agent-answer-form/SKILL.md) | 複数質問のHTML提示時 | questions.json、answer-form.html | 提示前、Skill外許可作業dir。JSON/HTML提示、回答Markdown照合 | HTML回答・Markdown返却 | Skill外の許可作業dir。questions.json / answer-form.htmlはCLI例。継続質問の元定義・回答と、定義変更前の旧HTMLを回収に必要な間保全（共通運用契約） |
| [test-requirements-analysis](../../skills/test-requirements-analysis/SKILL.md) | QA目的・品質目標設定/改版 | QA要求canonical JSON packet、表示Markdown | 草案・承認・保存検証、指定provider | 目的・品質目標・scope承認 | canonical JSON packet・表示Markdown。指定先の必要保存能力 |
| [test-architecture-design](../../skills/test-architecture-design/SKILL.md) | QA要求後、方式改版 | Architecture canonical JSON packet、表示Markdown | 承認後正本保存、指定provider | 方式・環境・分担承認 | canonical JSON packet・表示Markdown。指定先の必要保存能力 |
| [test-management](../../skills/test-management/SKILL.md) | 計画策定・改版・進捗 | 計画canonical JSON packet、母集団、進捗、是正・履歴 | 計画確定/改版/monitoring、指定provider | 計画・資源・終了基準承認 | canonical JSON packet・表示Markdown。指定先の必要保存能力 |
| [test-analysis](../../skills/test-analysis/SKILL.md) | 対象理解後、Risk変更 | Product Risk、重点・深度・技法候補 | 分析確定・局所変更後、指定先 | 必要時業務影響・リスク受容 | 指定先・Machine Entity/Runtime形式 |
| [test-item-analysis](../../skills/test-item-analysis/SKILL.md) | 機能/仕様理解後、item変更 | ITEM候補、階層、履歴 | 候補確定後、指定provider CAS/readback | 根拠不足・保存承認 | test-item-candidates-v1、指定provider |
| [test-condition-analysis](../../skills/test-condition-analysis/SKILL.md) | 共通条件候補識別、根拠変更 | COND候補、履歴、候補照合 | 候補確定後、指定provider CAS/readback | 根拠不足・保存承認 | test-condition-candidates-v1、指定provider |
| [test-requirement-design](../../skills/test-requirement-design/SKILL.md) | 仕様・Risk分析後 | TR、検証責務、上流追跡 | 設計・runtime検証後、指定先 | 固有の進行承認は原則不要、未決仕様への回答 | 指定先・TR/runtime契約 |
| [test-condition-design](../../skills/test-condition-design/SKILL.md) | TR後 | TCN、CI、技法、適用判断、期待結果候補 | 設計・runtime検証後、指定先 | 固有の進行承認は原則不要、必要な除外/仮定承認 | 指定先・TCN/CI/runtime契約 |
| [test-case-design](../../skills/test-case-design/SKILL.md) | TCN/CI後 | TC、前提、データ、手順、期待結果 | 設計・runtime検証後、指定先 | 固有の進行承認は原則不要、根拠不足時の回答 | 指定先・TC/runtime契約 |
| [e2e-test-selection](../../skills/e2e-test-selection/SKILL.md) | 自動化対象選定・価値変更 | 選定record、理由、履歴 | 選定検証後、指定先 | 自動化目的・対象 | 指定先・担当形式（選定record・履歴） |
| [coverage-analysis](../../skills/coverage-analysis/SKILL.md) | 設計/実装後、変更/修正後 | coverage、閉鎖性、gap、修正先 | 検証後、指定先 | 対象外・残存risk判断時 | 指定先・担当形式（coverage） |
| [adversarial-review](../../skills/adversarial-review/SKILL.md) | 成果物・コードの独立レビュー | 指摘、重大度、根拠、処置状態 | 保存依頼・継続利用時はレビュー後、指定先。単発は対話回答可 | 判断を要する指摘への回答 | 指定先・担当形式（レビュー） |
| [e2e-test-inspection](../../skills/e2e-test-inspection/SKILL.md) | E2E実装前、条件不足時 | repo、実効設定、安全条件、実装可否 | 必要な調査成果物のみ指定先。コード変更なし | URL・認証・データ・副作用 | 指定先・担当形式（調査）。実装・実行なし |
| [e2e-test-implementation](../../skills/e2e-test-implementation/SKILL.md) | inspection済み実装依頼 | Playwrightコード、実装参照、静的/軽量検証 | 変更許可・検証後、対象repo既存構成 | 変更範囲・必要正式反映承認 | 対象repoの構成。実装記録は指定先 |
| [e2e-test-execution](../../skills/e2e-test-execution/SKILL.md) | 既存/実装済みE2E実行 | Run、primary、attempt、raw、cleanup | preflight前提固定、実行後証跡・結果、指定先 | 実行条件・副作用上限許可 | 実効reporter/output設定・指定先。機密証跡はSection 4の制約に従い保護 |
| [e2e-test-result-analysis](../../skills/e2e-test-result-analysis/SKILL.md) | 異常・未実行・cleanup問題・分析依頼 | 原因分析、追加証拠、修正routing | 検証済みrawを参照し分析後、指定先 | 必要な原因情報 | 指定先・担当形式（分析、raw参照） |
| [e2e-test-reporting](../../skills/e2e-test-reporting/SKILL.md) | E2E実行・必要分析後 | 人間向けE2E報告 | 報告後、指定先。raw再判定なし | 結果確認 | 指定先・人間向け報告形式 |
| [test-target-inspection](../../skills/test-target-inspection/SKILL.md) | Live UI事実・鮮度確認 | 対象資料、任意snapshot | snapshotを永続保存する場合は先に保存・identity確認後資料更新、指定先のみ | URL・操作許可・証跡制約 | 明示保存先。snapshotは任意、保存要求時のみ完了条件 |
| [test-execution](../../skills/test-execution/SKILL.md) | 詳細TCのAI直接実行 | 実行前YAML、Run、観測、TC結果、cleanup | 実行前条件固定、実行後Markdown/証跡、指定先 | 環境・準備・操作許可 | 最終Markdownに実行前YAMLを保持。証跡はSection 4の制約に従い保護 |
| [testware-implementation](../../skills/testware-implementation/SKILL.md) | 非E2Eコード/fixture/設定実装 | testware、実装参照、軽量検証 | 隔離作業・検証・認可後、対象repo | 変更範囲・必要保存承認 | 対象repoの構成・許可範囲 |
| [testware-execution](../../skills/testware-execution/SKILL.md) | 非E2E runner/静的解析実行 | Run、raw参照、attempt、診断、cleanup | preflight・実行後、指定先。分析/raw分離 | 環境・操作・必要予約許可 | repo外の保護された指定artifact root、manifest.json・attempt log等 |
| [regression-testing](../../skills/regression-testing/SKILL.md) | baseline更新、変更、定期実行依頼 | Baseline、membership、Run、Activity、履歴 | 選定・Activity確定時、Section 14/明示root | 初回方針、必要実行条件 | Section 14/明示root/direct ref、baseline/run/activity形式 |
| [exploratory-testing](../../skills/exploratory-testing/SKILL.md) | 探索・owner不明hypothesis | Charter、Session、Finding、Observation | Charter固定後、観測/終了時、Section 14/明示root | 目的・scope・timebox・操作許可 | Section 14/明示root/direct ref、Charter/Session形式 |
| [context-signal-audit](../../skills/context-signal-audit/SKILL.md) | 単一sourceの中立signal抽出・再利用・訂正 | context-signal-batch、不変の訂正batch、試行状態 | 抽出成功・範囲確定後、create-if-absentと独立readback。必須時は開始要求・attemptを既存stateへ登録 | source・対象範囲、必要なroot・権限 | 指定artifact rootの `context-signal-batch/<identity>.json`、stateは既存SQLite |
| [context-rule-synthesis](../../skills/context-rule-synthesis/SKILL.md) | 横断法則候補・反例・差異条件・再評価 | context-rule-candidate、context-synthesis-run、必要handoff | in_progress run保存後、条件付き候補更新・独立readback、必要handoff・完了。必須時は開始要求とrun参照を既存stateへ登録 | 分析範囲、必要なroot・権限、既存ownerで必要な承認 | 指定artifact rootの `context-rule-candidate/<identity>.json`・`context-synthesis-run/<identity>.json`、stateは既存SQLite |
| [qa-knowledge](../../skills/qa-knowledge/SKILL.md) | candidate triage、再検証、更新 | entry、根拠、適用範囲、履歴 | entry単位CAS/readback、knowledge root | 必要時保存・採否判断 | qa.knowledge_root/`<entry-ref>.md`、更新はnative CAS |
| [defect-management](../../skills/defect-management/SKILL.md) | FAIL/Finding/Observation後 | 欠陥候補、Issue参照、修正確認依頼 | 候補整理・認可済み操作後、指定先/Issue tracker | 外部Issue操作認可 | qa.defect_issue_tracker_ref。候補文書は指定先 |
| [test-reporting](../../skills/test-reporting/SKILL.md) | 統合報告、終了基準確認 | 読取専用snapshot、母集団、完全性 | 集計検証後、指定先。元結果不変 | 結果・リリース判断 | immutable snapshot_ref、指定providerのcreate-if-absent |
| [test-evaluation](../../skills/test-evaluation/SKILL.md) | QA活動終了・改善効果確認 | 5軸評価、改善状態、効果測定、引継ぎ | 評価・状態移行後、指定先 | 改善採否・受領 | 指定先・担当形式（評価・改善・引継ぎ） |
| [usability-evaluation](../../skills/usability-evaluation/SKILL.md) | 保存済みUI資料のUX評価 | 評価、根拠、改善案 | 評価後必要時指定先、browser操作なし | 資料・目的 | 指定先・担当形式（資料評価） |
| [usability-inspection](../../skills/usability-inspection/SKILL.md) | Live Web UI使用性・測定 | 観測、測定、証跡、cleanup | 観測後、明示安全な保存先・必要handoff | URL・scope・操作/保存許可 | 安全な指定先・担当形式（観測・証跡） |
| [wcag-conformance-evaluation](../../skills/wcag-conformance-evaluation/SKILL.md) | formal WCAG評価依頼 | Plan、sample、結果、report、EARL | Plan登録、観測handoff、closure/readback後、指定先/qa.workflow_state_rootのlocal SQLite | 対象、版、level、評価責任・scope | qa.workflow_state_root配下のworkflow-state.sqlite3（単一hostのlocal filesystem）、外部report/EARL配置は指定 |

## 保存先・設定の指定

担当Skillが必要とする保存先・実行条件だけを指定する。[Project Context template](../../skills/qa-workflow/assets/project-context-template.md)の設定キーを使用する経路では、該当するキーを利用し未設定値を自動生成しない。

<!-- dprint-ignore -->
| キー / 記録箇所 | 用途 |
| --- | --- |
| qa.workflow_state_root | persisted state、claim、対応WCAG固有state、必須横断コンテキスト分析の要求・attempt・run参照（SQLite） |
| 横断コンテキスト分析の指定artifact root | 3 kindのroot相対ref。呼出し側が指定し、既存権限・保存条件に従う |
| qa.knowledge_root | project-local knowledge entry（1 entry = 1 artifact） |
| qa.feature_artifact_root | 機能台帳root |
| qa.reservation_root | 予約保存先候補。native予約/解放の証明ではない |
| qa.feature_source_refs / qa.feature_base_ref / qa.feature_approval_policy_ref | 機能情報源、基準revision、承認方針 |
| qa.regression_scope / qa.regression_policy / qa.auxiliary_testware_refs | Regression範囲、選定、補助testware参照 |
| qa.defect_issue_tracker_ref | 外部Issue管理先。未設定なら外部更新しない |
| Section 10 | 進行モード。利用者の明示指定がない場合のcontinuous / gated |
| Section 12 / 13 | DEC / ASM正本一覧（別正本を指定する場合はそのowner） |
| Section 14 | 既存QA成果物、Regression/Exploration履歴のrootまたはref、範囲、鮮度 |
| Section 4 | 実行環境、認証取得方法、共有resource、許可上限、cleanup、証跡制約 |

保存先・承認policy・provider能力等が担当契約の必須条件を満たさない操作は停止する。設定の詳細は担当Skillの契約に従う。ローカルSQLiteは対応用途に限定し、遠隔保存能力をローカルfixtureから推定しない。

## UI target package

[専用schema](../../skills/spec-analysis/references/ui-test-target-analysis.md)の必須payloadはREADME.md、00、01、02、06、07、09、CHANGELOG.md。MANIFEST.mdは必須control file。03/04/05/08はTriggerに応じた条件付きfile。10以降は00で宣言した案件固有extensionのみ。09はAuthorityとtraceabilityの正本。ui-target-analysisは00のUI操作判定、01のUI構造・遷移、02のUI操作一覧を担当する。spec-analysisはUS/UC/Behavior/AC、業務ルール、期待値、Authority、UNKNOWNを担当する。論理ownerは情報・行単位で分離し、既存ui_target_package.py materializeを単一writerとする（[UI分析の責務](../../skills/ui-target-analysis/references/guidance.md)）。

引継ぎの最低情報・依存整合・保存結果不明時の扱いは[共通運用契約](qa-workflow-operating-contract.md)を参照する。
