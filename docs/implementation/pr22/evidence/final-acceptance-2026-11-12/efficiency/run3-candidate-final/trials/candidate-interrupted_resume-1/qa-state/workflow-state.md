# ワークフロー状態: カート QA（テスト分析〜テスト観点・条件設計）

- 対象製品: `product/`（commit `2a8bcf57`。ユーザー指定。workspace は git 管理外のため commit との直接照合は未実施）
- 対象機能: カート（`product/docs/spec/features/cart.md`）
- 要求成果物: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ項目）設計
- 実施範囲外: テストケース設計、実行、カバレッジ分析、反証レビュー、E2E
- 進行モード: continuous（既定。ユーザー指定なし）
- 製品ファイル・仕様書: 変更していない

## 前回中断からの再開

- 前回: `01-spec-analysis.md` のみ存在。`workflow-state.md` は存在せず（01 が参照していた sha256 記録先が欠落）。
- 完了済み工程: `spec-analysis`（01）
- 未完了工程: `question-analysis`（Q-01〜Q-12 の分類が未文書化）以降すべて
- 今回の対応:
  1. 01 の入力 sha256 を再計算して照合 → **全件一致（再利用可）**。`storefront.md` のみ未記録だったため、今回の値を基準として記録する。
  2. 01 を再利用し再生成しない。
  3. 未完了工程を再開する。

## 入力 revision と再利用判定

照合スクリプト: `qa-state/scripts/hash_inputs.py`（読み取り専用。sha256 先頭12桁）

| 入力                                    | 記録値（01） | 今回値       | 判定                     |
| --------------------------------------- | ------------ | ------------ | ------------------------ |
| features/cart.md                        | 385777e56a0d | 385777e56a0d | 同一                     |
| roles-and-permissions.md                | 519731749c55 | 519731749c55 | 同一                     |
| state-and-scenarios.md                  | ccd0cab4b0bd | ccd0cab4b0bd | 同一                     |
| product-scope.md                        | 23508ebe243d | 23508ebe243d | 同一                     |
| ui-ux-contract.md                       | ac9b86d99ff6 | ac9b86d99ff6 | 同一                     |
| unresolved-specifications.md            | c3ac09d0f145 | c3ac09d0f145 | 同一                     |
| known-deviations.md                     | 518d110c069d | 518d110c069d | 同一                     |
| checkout-and-payment.md                 | 9877302a255e | 9877302a255e | 同一                     |
| authentication.md                       | 3334ecd7b5fb | 3334ecd7b5fb | 同一                     |
| features/storefront.md                  | 未記録       | 3f77926ad163 | 基準値として新規記録     |
| 03_domain/business_rules.md             | 8fe29aa8a481 | 8fe29aa8a481 | 同一（権威は未決: Q-01） |
| 12_quality/acceptance_criteria.md       | cb057739f878 | cb057739f878 | 同一（権威は未決: Q-01） |
| 12_quality/requirements_traceability.md | 3ad9acafa315 | 3ad9acafa315 | 同一                     |

- 判定: `01-spec-analysis.md` は **再利用（入力 revision 同一）**。
- 今回の変更箇所: なし。下流の `要再検証` 対象なし。

## 工程状態

| 順 | Skill                   | 対象 / 実行範囲                                    | 状態                                 | 成果物                          | 備考                                           |
| -- | ----------------------- | -------------------------------------------------- | ------------------------------------ | ------------------------------- | ---------------------------------------------- |
| 1  | spec-analysis           | カート（現在有効な仕様根拠）                       | 完了（再利用）                       | `01-spec-analysis.md`           | 入力同一                                       |
| 2  | question-analysis       | Q-01〜Q-13 の分類・保留（Q-13 は条件設計中に追加） | 完了                                 | `02-question-analysis.md`       | 回答なし。ブロック中範囲を確定                 |
| 3  | test-analysis           | `テスト分析`                                       | 完了                                 | `03-test-analysis.md`           | 既定の機能別リスク。案件固有リスク方式は未確認 |
| 4  | test-requirement-design | `テスト要求`                                       | 完了（ブロック中 12件を残す）        | `04-test-requirement-design.md` | TR-001〜TR-030                                 |
| 5  | test-condition-design   | `テスト観点・条件`                                 | 完了（ブロック中 TR は条件化しない） | `05-test-condition-design.md`   | TCN-001〜013、CI 49件                          |
| 6  | coverage-analysis       | —                                                  | 対象外（今回の範囲外）               | —                               |                                                |

保留の一覧: `pending-approvals.md`（承認が必要な 13 件）。

## 機械証拠（runtime-v2）の扱い

- `workflow_runtime.py` / 各Skillの `runtime_contract.py` の dispatch・`verify_runtime_evidence` は **今回未実行**。
- 理由: canonical な `workflow_ref`（UUID）と、current な Machine Entity（Authority / Risk 等）の入力が `qa-state/` に存在しない。手組みで代替しない。
- 影響: 本成果物は人間向けの Markdown 成果物であり、runtime-v2 の完了証拠は持たない。`can_complete` 相当の機械判定は得られていない。
- 再開条件: runtime-v2 の入力（workflow_ref と Authority Entity）を用意した後に、各Skillの `verify_runtime_evidence` を実行する。

## 保留（承認が必要な項目）

詳細は `pending-approvals.md`。影響するテスト要求（TR）は「ブロック中」として残し、先へ進めていない。

## 自己検証（オーケストレーション）

- 開始点: spec-analysis から再開（既存成果物を再利用）。
- 停止条件: 仕様権威（Q-01）、統合超過（Q-02）等のブロッカーは影響範囲だけに限定し、全体は停止していない。
- 修正ルーティング: ブロッカーは question-analysis → 承認者へ。仕様の決定は spec-analysis へ戻す（本ワークフロー内では決めていない）。
- 完了判定: テスト分析〜条件設計の範囲は完了。ただしブロック中 TR が残るため、要求範囲全体は「部分完了（ブロック中あり）」。
