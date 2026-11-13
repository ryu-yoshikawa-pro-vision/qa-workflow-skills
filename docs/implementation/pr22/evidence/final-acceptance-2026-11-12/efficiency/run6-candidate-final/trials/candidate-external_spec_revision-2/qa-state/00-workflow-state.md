# ワークフロー状態: カート機能 QA（テスト分析〜テスト観点設計）

- ワークフロー全体状態: 部分完了（ブロック中あり）
- 開始Skill: qa-workflow（オーケストレーション）
- 開始対象 / 実行範囲: カート機能 `product/docs/spec/features/cart.md` / テスト分析からテスト観点（条件）設計まで
- 最終Skill: test-condition-design
- 最終対象 / 実行範囲: テスト条件・カバレッジ項目の定義まで。テストケース化（test-case-design）、実行、報告は範囲外
- 入力revision:
  - 製品commit: 2a8bcf57（依頼者の申告。workspaceはgit repositoryではないため照合できていない）。製品コードは本改版で変更していない
  - 仕様: `product/docs/spec/features/cart.md`（版番号の記載なし）。改版後の内容は `product-change-spec.diff` の適用結果。差分は BR-CART-001 の上限値 99 → 50 の1行のみ
  - 参照: `product/docs/12_quality/acceptance_criteria.md`（改版対象外）、`product/docs/03_domain/business_rules.md`（改版対象外。上限値99のまま。齟齬 Q-CART-13）、`product/src/domain/services/cart.ts`、`product/src/application/use-cases/cart-use-cases.ts`（観測用。期待仕様の根拠には使わない）
- 開始時の確認（改版対応）:
  - 既存成果物（01〜06、pending-approvals）あり。`input-revisions.json` は未作成のため `input_revision.py compare` は `no_record`。前回の入力（BR-CART-001 = 99）は前回成果物の記述と差分の before 側で一致することを確認し、変更範囲を差分どおりに特定した
  - 再実行（影響範囲のみ）: spec-analysis（SPEC-CART-02、IMPL-01、UNK-CART-12）、question-analysis（Q-CART-11〜13）、test-analysis（RISK-CART-01の重点・発生しやすさ、技法）、test-requirement-design（TR-CART-01、TR-CART-25追加）、test-item-analysis（ITEM-CART-01）、test-condition-design（CND-CART-001/007、CND-CART-010追加）
  - 再利用（変更なし）: 01・02・03・04・05・06 の上限以外の全条件（統合、権限、価格ゲート、画面状態、保留の条件）
  - 未実施のまま（前回から変更なし）: coverage-analysis、test-case-design以降
- 中断・再開の記録: 改版対応の途中中断なし。承認待ち（Q-CART-12 / 13）は保留のまま残す

## Project Context と永続化

- 案件のProject Contextが見つからなかった（`qa.workflow_state_root`、`qa.reservation_root`等の定義なし）。
- そのため永続workflow state、`workflow_runtime.py`、owner verifierは実行していない。本ディレクトリのMarkdownが成果物の正本であり、runtime検証済みではない。
- Project Contextの配置・編集方針は承認事項として保留（`pending-approvals.md` PA-1）。

## Skill別状態

| Skill                      | 対象 / 実行範囲              | 状態                           | 成果物                    | ブロッカー / 備考                                                                                           |
| -------------------------- | ---------------------------- | ------------------------------ | ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| project-context            | 案件配置                     | ブロック中（承認待ち）         | -                         | PA-1。Markdown成果物の保存は継続可能                                                                        |
| feature-analysis           | カート機能の機能ID           | 省略                           | -                         | 機能階層の確定は今回の範囲外。カート機能は単一specとして扱う                                                |
| spec-analysis              | cart.md + 受入基準           | 完了（局所適用・改版反映済み） | `01-spec-analysis.md`     | 直接適用。改版: SPEC-CART-02を50へ。齟齬UNK-CART-12。spec-analysis SKILL.mdの出力契約への適合は未検証       |
| question-analysis          | 仕様の曖昧さ・欠落           | 完了（局所適用・改版反映済み） | `02-questions.md`         | ブロッカー1件、要確認多数。改版起因で Q-CART-12（承認待ち）・Q-CART-13 を追加。保留は`pending-approvals.md` |
| test-analysis              | リスク・重点・レベル         | 完了（局所適用・改版反映済み） | `03-test-analysis.md`     | リスク評価は定性的。RISK-01を改版に合わせて更新（重点・発生しやすさ High）                                  |
| test-requirements-analysis | QA目的・品質目標             | 範囲外                         | -                         | 依頼にQA目的・品質目標の指定なし。Phase 1受入基準を入力として使用                                           |
| test-architecture-design   | レベル・環境・データ全体設計 | 範囲外                         | -                         | `03`の推奨レベルに留める                                                                                    |
| test-management            | 計画・進捗                   | 範囲外                         | -                         | -                                                                                                           |
| test-item-analysis         | テストアイテム               | 完了（局所適用・改版反映済み） | `05-test-items.md`        | 安定ID未発行（ITEM IDは候補）。ITEM-CART-01は50へ更新、実装不一致を注記                                     |
| test-condition-analysis    | 共通テスト条件候補           | 省略                           | -                         | 共通COND台帳は未整備。今回は案件内の条件設計に集中                                                          |
| test-requirement-design    | テスト要求                   | 完了（局所適用・改版反映済み） | `04-test-requirements.md` | TR-CART-01更新、TR-CART-25追加                                                                              |
| test-condition-design      | 条件・カバレッジ項目         | 完了（局所適用・改版反映済み） | `06-test-conditions.md`   | CND-CART-001/007更新、CND-CART-010追加。Q-CART-01 に依存する条件は「保留」扱いのまま                        |
| coverage-analysis          | 設計全体の閉鎖性             | 未実施                         | -                         | 範囲外。改版後も前回どおり未実施。必要なら次工程前に実施                                                    |
| test-case-design 以降      | -                            | 範囲外                         | -                         | -                                                                                                           |

## 実施上の制約（重要）

- 各担当Skillの手順は本セッションで直接適用した。担当Skillを個別に起動してはおらず、各SKILL.mdの出力契約・validatorでの検証は行っていない。
- 観測用に読んだ実装コードは期待仕様として扱っていない。実装と仕様が食い違う点は`02-questions.md`へ記録した。

## 次の一手

1. `pending-approvals.md`の保留項目に回答を得る。改版起因では、Q-CART-12（BR-CART-001の50 と AC-CART-001の99の齟齬。50を現行とする仮定の承認）と Q-CART-13（business_rules.md の99の扱い）を優先する。従来どおり Q-CART-01（在庫・購入上限の減少時に既存明細をどう扱うか）も必要。
2. 回答後、影響する条件（`06`の該当行）だけを再検証対象として戻す。Q-CART-12 が「99が現行」となった場合は CND-CART-001/007/010、TR-CART-01/25、RISK-01 の境界値を作り直す。
3. 実装（`CART_QUANTITY_LIMIT = 99`）は製品コードを変更しないため、TC実行時に51〜99の受理を欠陥候補として扱う（defect-managementへ）。
4. 承認後にtest-case-designへ進める（今回の依頼の範囲外のため未実施）。
