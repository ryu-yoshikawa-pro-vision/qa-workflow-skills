# QA全工程の実装Planインデックス（PR #22関連）

## 目的・対象

この索引は、`qa-workflow-skills`の**QA全工程を支援する**という確定方針と、PR #22に収めた実装Planの役割を区別する。対象は以下のPlanと調査レポートに限る。過去の`docs/plans/`全件を列挙する索引ではない。

全工程への支援は、全工程の固定順実行、あらゆる技術の自動実行保証、Agentによる製品改修・リスク受容・リリース承認を意味しない。案件の要求・有効な既存成果物に応じて開始し、必要な工程だけ実行・再利用・再開する。

## 計画と根拠を読む順序

1. **本索引**：目標、各Planが所有する責務、依存関係、実装時の判断規則。
2. **[開発変更とQA成果物の追跡Plan](./2026-11-07_122247_development-qa-traceability.md)**：製品機能・仕様・テストアイテム・共通条件候補の識別、正式設計への接続、PR／merge／release変更追従。新規6 Skillの設計と既存runtime／CI移行を所有する。以下では「開発連動QA Plan」と呼ぶ。
3. **[QA全工程の追加責務Plan](./2026-11-07_170134_qa-full-process-implementation.md)**：QA要求分析、テストアーキテクチャ、テスト計画・管理、欠陥管理、統合報告、QA活動評価の6つの責務を所有する。以下では「QA全工程Plan」と呼ぶ。
4. **[非Webのテスト実装・実行詳細Plan](./2026-11-07_170134_qa-full-process-implementation_01_test-implementation-and-execution.md)**：API・バッチ・コンポーネント・イベント／外部連携、非機能、静的テストについて、テストコード／fixtureの実装・更新・検証と実runnerによる実行・結果・cleanupまで。QA全工程Planの詳細文書であり、Playwright既存契約を再実装しない。
5. **[保存・承認・集計・実Agent受入の共通契約](./2026-11-07_170134_qa-full-process-implementation_02_storage-approval-reporting.md)**：追加責務の条件付き書込み・承認主体の認証、正式Issue更新、計画上の実行母集団と取得結果の照合、独立基準データによる検証。QA全工程Planの詳細文書であり、開発連動QA Planの新規機能台帳や製品CIの正本を置き換えない。
6. **[目的・工程対応とレビュー記録](../reports/2026-11-07_qa-process-responsibility-and-artifact-contract-review.md)**：確定済みQ01〜Q08、現行23 Skillとの工程対応、当時の未解決課題・判断根拠。実装契約の正本ではなく調査時点の記録として読む。

## Planごとの責務

### 開発連動QA Planが変更・検証するもの

- `project-context`：案件のProject Contextの発見・作成・更新・参照・履歴を管理する。既存16節／stable key／DEC・ASMの互換性を守る。
- `feature-analysis`：製品機能の候補・安定ID・根拠・ソース範囲・変更差分を管理する。
- `ui-target-analysis`：UI構造・操作・画面状態を管理し、製品の期待仕様Authorityは`spec-analysis`に残す。
- `test-item-analysis`：テストアイテムを製品機能とは別IDで管理する。
- `test-condition-analysis`：共通テスト条件候補の識別・安定ID・履歴を管理する。正式TCNは`test-condition-design`。
- `e2e-test-selection`：技術非依存のE2E選定・理由・履歴を管理する。
- 上記の既存Skill／runtimeへの接続、開発差分の正規化、PR／merge／releaseの現在性検証、製品CIへの保存成果物の受渡し、既存UI package移行、既存設計・coverageの互換性。

**担当しないこと**：QA案件のテスト計画・工数・進捗管理、正式欠陥の外部追跡、全方式の統合報告、QA活動効果の評価、非Web向けのテストコード・runner実装。機能抽出と製品CIだけでこれらの責務を完了したと扱わない。

### QA全工程Planが変更・検証するもの

- `test-requirements-analysis`：QA活動の目的・品質目標・要求元・対象／制約・合意。
- `test-architecture-design`：テストレベル・タイプ・方式・環境・データの全体設計。局所的なProduct Riskは`test-analysis`、具体的TCN・CIは既存設計owner。
- `test-management`：計画・監視・コントロール、プロジェクトリスク、是正、開始・終了基準。Skillのrouting stateは`qa-workflow`。
- `defect-management`：欠陥候補の根拠・外部Issue引継ぎと追跡、修正確認の依頼・結果参照。正式Issueの状態は外部サービス、再実行・判定は既存実行owner。
- `test-reporting`：複数のテスト方式のraw結果・対象build・計画上の母集団を参照する統合snapshot。元runとPASS/FAILを更新しない。
- `test-evaluation`：QA活動の効果・効率・改善・保管・引継ぎの評価。Skill自体の評価は`EVALS.md`。
- 非Web・非機能・静的テストの実装・実行の接続、追加責務の保存・承認・集計・実Agent受入については、上記2詳細文書を正本とする。

**担当しないこと**：開発連動QAの機能ID・アイテムID・共通条件候補の採番／更新、製品仕様Authority、Product Risk、既存TR／正式TCN／CI／TC、Regression Run、実行ownerのraw結果や製品CIの開発差分検証。

## 実装時の責務決定規則

1. **製品機能や変更差分の母集団が不足**：開発連動QA Planの`feature-analysis`／source acquisitionへ戻す。
2. **期待仕様が不明・競合**：既存`spec-analysis`／`question-analysis`へ戻す。実装・観測を無断でAuthorityにしない。
3. **QA活動の要求・目標・開始／終了基準が不明**：QA全工程Planの要求分析／`test-management`へ戻す。個別TRと案件QA目標を混同しない。
4. **テストレベル／タイプの割当**：案件・ユーザーの明示指定、承認済みアーキテクチャ割当、既存`test-analysis`既定システムテストの順。矛盾した部分だけ判断元へ戻し、変更影響があるTR/TCN/CI/TCを再検証する。
5. **テストアイテム・共通条件候補と正式TCNの識別**：前二者は開発連動QA Plan、正式採否・TCNは既存`test-condition-design`、具体的TCは`test-case-design`。
6. **テスト実装・実行**：Playwright固有の既存Skillを維持する。API・バッチ等の実装・実行の責務は非Web詳細Planへ。対象SUTの製品改修は含めない。
7. **FAIL・Observationから欠陥候補を管理**：実測・原因分析の正本は実行owner、QA側の追跡は`defect-management`、正式Issueは外部システム。修正確認は既存TC／testwareを使って実行ownerへ依頼する。
8. **集計・完了判断**：計画上の対象source一覧は`test-management`、各実測はsource owner、横断集計は`test-reporting`、活動評価は`test-evaluation`。workflowの完了と製品テストのPASS／リリース可否を混同しない。
9. **保存・承認・競合**：担当するデータのownerは各Skillのまま。provider-native CAS、対象scope／revisionと認証された承認主体、取得完全性・受入証拠の共通条件は保存・承認・集計の詳細文書で検証する。
10. **Skill選択・局所停止・再開**：既存`qa-workflow`を再利用する。別の中央オーケストレーターや第二のartifact graphを追加しない。

## 依存・実装順序と完了の扱い

1. **既存baseline**：`main`とPR #22／PR #17／PR #10の差分・CI、既存owner・consumer・runtime・storageと直接開始経路を確認する。PR #17は`qa-workflow`、`test-analysis`、評価runtime／CIの変更を含むので、該当実装時に競合を再点検する。
2. **開発連動QAの作業**：開発差分・製品機能・spec／UI・item／条件候補・正式テスト設計への追跡と、CI・保存・承認・移行を既存Planの全完了条件に従って実装・検証する。
3. **QA全工程の追加責務**：PR #22の新Skillがない状態でも既存仕様／TC／実行結果を利用した単独経路を実装・受入できる。6つの担当領域と非Webの実装・実行、共通契約を欠かさない。
4. **実成果物間の統合**：PR #22実装後、feature／item／条件候補のID・source revision・履歴とQA要求・計画・報告を実際に接続する。**計画上の型だけの照合は統合受入を満たさない**。ID移行、並行更新、既存成果物再利用、局所stale・復旧を確認する。
5. **最終完了ゲート**：開発連動QAの既存Planの15完了条件と、QA全工程Planの10完了条件、2詳細文書の完了条件、実Agent／実runner／実provider受入をそれぞれ確認する。一方の成功を他方の未検証の代用にせず、未実行／SKIP／権限不足は独立して記録する。

**PRの位置付け**：PR #22はこれらの計画・調査文書を保存する文書変更PR。Skill・runtime・CI・製品実装を変更したわけではない。将来の実装PRの数や担当は別途作業指示に従い、どの実装PRでも上記の契約と未完了条件を維持する。

## レビュー指摘と修正箇所

- P1-1 非Webテストコード実装のowner欠落 → 非Web実装・実行詳細Plan。
- P1-2 テストレベル決定の重複 → QA全工程Planの`test-architecture-design`と本索引の優先順位。
- P1-3 native CASと保存先の未確定 → 保存・承認・集計の詳細文書（provider検証・競合試験・blocked）。
- P1-4 統合報告の母集団不明 → `test-management`と`test-reporting`のsource inventory契約。
- P1-5 承認・外部Issue認可の証拠不足 → 保存・承認・集計の詳細文書（認証主体・scope・revision・重複防止）。
- P2-1 PR #22未実装時と実装後の受入の混同 → 本索引の順序・QA全工程Planの独立した完了ゲート。
- P2-2 実Agent受入の正解／負例不足 → 保存・承認・集計の詳細文書の独立基準ケース。
- P2-3 PR本文の変更内容が古い → PR本文に現行の文書構成・検証状況を反映する。

## 実装開始時の確認事項

- 各Skillで利用するsource ref、stable ID、現在性・schema・Migrationの既存契約と参照先。
- Project Contextに指定された保存先のnative conditional writeと履歴取得、承認ポリシーと認証主体、外部Issueシステムの書込み権限・冪等操作。
- API・バッチ・コンポーネント、非機能測定、静的レビューに使う具体的なrunner／CLI／対象repo。使えると仮定して未実装・未実行をPASSにしない。
- 独立した基準データ、形式／意味／実Agent／実runner評価、既存回帰とCI、証拠の保存先・秘密情報・外部操作の許可。

未確定の案件固有値は理由・影響範囲と再確認先を記録し、完了条件が要求する実機能・証拠を無断で省略しない。
