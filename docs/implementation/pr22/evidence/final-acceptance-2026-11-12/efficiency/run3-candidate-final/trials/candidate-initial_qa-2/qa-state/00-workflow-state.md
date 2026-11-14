# QAワークフロー状態: カート（Cart）

## 要求

- 対象: カート機能（`product/docs/spec/features/cart.md`）
- 実施範囲: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ基準・項目）設計まで
- 除外: テストケース詳細化（`test-case-design`）、カバレッジ分析（`coverage-analysis`）、独立レビュー（`adversarial-review`）、テスト実行、製品コード・仕様書の変更
- 承認が必要な項目: `05-pending-and-questions.md` に保留として記録（先へ進めていない）

## 入力revision

| 項目                                                                                                                                                                          | 値                                                                                                  | 確認状況                                                              |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 製品commit                                                                                                                                                                    | `2a8bcf57`（依頼者の指定）                                                                          | `product/` に `.git` が存在しないため、本セッションでは検証していない |
| `docs/spec/features/cart.md`                                                                                                                                                  | sha256 `385777e5…7216`（5308 bytes）                                                                | 計算済み                                                              |
| 関連仕様（README, product-scope, roles-and-permissions, state-and-scenarios, unresolved-specifications, known-deviations, storefront, checkout-and-payment, native-customer） | 指紋は計算済み（同じ計算結果は本セッションの作業記録に残る）                                        | 参照のみ                                                              |
| 案件Project Context（QA用）                                                                                                                                                   | 未発見。`product/docs/PROJECT_CONTEXT.md` は製品開発用の運用文書で、QA案件のProject Contextではない | `project-context` は未実行                                            |
| 既存QA成果物                                                                                                                                                                  | なし（`qa-state/` は空）                                                                            | 再利用対象なし                                                        |

## Skill実行状態

| Skill                     | 対象 / 実行範囲           | 状態                                     | 成果物                        |
| ------------------------- | ------------------------- | ---------------------------------------- | ----------------------------- |
| `spec-analysis`           | カート（BR/AC/画面状態）  | 完了（手作業、runtimeなし）              | `01-spec-authority.md`        |
| `question-analysis`       | 仕様の曖昧さ・欠落の分類  | 完了（分類のみ、正式な回答収集は未実施） | `05-pending-and-questions.md` |
| `test-analysis`           | `テスト分析`              | 完了（手作業、runtime未実行）            | `02-test-analysis.md`         |
| `test-requirement-design` | テスト要求                | 完了（手作業、runtime未実行）            | `03-test-requirements.md`     |
| `test-condition-design`   | `テスト設計` の条件・観点 | 完了（手作業、runtime未実行）            | `04-test-conditions.md`       |
| `coverage-analysis`       | 範囲外                    | 未実行                                   | -                             |
| `adversarial-review`      | 範囲外                    | 未実行                                   | -                             |
| `test-case-design`        | 範囲外                    | 未実行                                   | -                             |

## 機械証拠（runtime）の扱い

- 各設計Skillの `runtime_contract.py` / `workflow_runtime.py` によるMachine Runtime Input / Result / Entity、`verify_runtime_evidence` の最終gateは **実行していません**。
- 理由: 本セッションではBashの実行権限がinline `python3 -c` を拒否され、runtimeの正規入力（stdin JSON envelope、前回成果物、current Entity）も用意していません。また、依頼のshell制約は `python3 <絶対path>` 形式のみです。
- したがって、本ディレクトリの成果物は **手作業で作成した設計草案であり、runtime検証済みではありません**。`verify_runtime_evidence` が必要な場合は別セッションで実行してください。
- workflow stateは `qa.workflow_state_root` が未設定のため、helperによる永続化を行わず、本Markdownを状態表として扱います。

## 完了判定

- テスト分析〜テスト観点・条件設計: 手作業成果物は作成済み。ただしruntime gate未通過のため「機械検証済み」とは判定しない。
- 未解決（ブロック中または保留）の項目は `05-pending-and-questions.md` に一覧化。
- ワークフロー全体（テストケース、実行、報告）は範囲外のため未完了。
