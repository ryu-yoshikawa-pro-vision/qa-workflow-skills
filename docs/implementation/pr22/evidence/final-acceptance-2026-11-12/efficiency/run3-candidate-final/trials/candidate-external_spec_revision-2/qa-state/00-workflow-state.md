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
| `docs/spec/features/cart.md`                                                                                                                                                  | sha256 `19635e51…1f25`（5308 bytes、改版後）                                                        | 計算済み（改版前は `385777e5…7216`）                                  |
| 改版差分 `product-change-spec.diff`                                                                                                                                           | sha256 `3ee1f3d1…b514`（644 bytes）。変更は BR-CART-001 の1行（99 → 50）のみ                        | 2026-11-13 受領                                                       |
| 関連仕様（README, product-scope, roles-and-permissions, state-and-scenarios, unresolved-specifications, known-deviations, storefront, checkout-and-payment, native-customer） | 指紋は計算済み（同じ計算結果は本セッションの作業記録に残る）                                        | 参照のみ                                                              |
| 案件Project Context（QA用）                                                                                                                                                   | 未発見。`product/docs/PROJECT_CONTEXT.md` は製品開発用の運用文書で、QA案件のProject Contextではない | `project-context` は未実行                                            |
| 既存QA成果物                                                                                                                                                                  | なし（`qa-state/` は空）                                                                            | 再利用対象なし                                                        |

## 改版影響（2026-11-13、product-change-spec.diff）

- 変更: BR-CART-001 の数量上限 `「在庫数」「購入上限数」「99」` → `「50」`。cart.md の AC-CART-001 本文は「99の各境界値」のまま未更新（矛盾。P-20）。
- 影響あり（更新済み・手作業）: `01`（SPEC行、AC行、A-02、A-05追加）、`02`（変更マップ、RISK-001、RISK-008追加、重点、着眼点、残存リスク）、`03`（TR-CART-001、改版差分節）、`04`（TCN-003とCI、TCN-007の例示、改版差分節）、`05`（P-19更新、P-20、P-21追加、次のステップ）。
- 影響なし（再計算不要）: TCN-001（実効上限5）、TCN-002（実効上限3）、TR-CART-002〜013、統合・再検証・ロール・画面状態の規則。
- 下流: `test-case-design` / `coverage-analysis` は範囲外で未作成のため、再検証対象はない。
- 補助文書の99残存（`03_domain/business_rules.md:137` 等）は正本ではないため変更していない。P-21 で確認。
- 製品コード・仕様書は変更していない。

## Skill実行状態

| Skill                                                                                                                    | 対象 / 実行範囲           | 状態                                                      | 成果物                        |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------- | --------------------------------------------------------- | ----------------------------- |
| `spec-analysis`                                                                                                          | カート（BR/AC/画面状態）  | 完了（手作業、runtimeなし）                               | `01-spec-authority.md`        |
| `question-analysis`                                                                                                      | 仕様の曖昧さ・欠落の分類  | 完了（分類のみ、正式な回答収集は未実施）                  | `05-pending-and-questions.md` |
| `test-analysis`                                                                                                          | `テスト分析`              | 完了（手作業、runtime未実行）                             | `02-test-analysis.md`         |
| `test-requirement-design`                                                                                                | テスト要求                | 完了（手作業、runtime未実行）                             | `03-test-requirements.md`     |
| `test-condition-design`                                                                                                  | `テスト設計` の条件・観点 | 完了（手作業、runtime未実行）。改版反映済み（2026-11-13） | `04-test-conditions.md`       |
| 改版反映（`spec-analysis` / `test-analysis` / `test-requirement-design` / `test-condition-design` の該当行のみ、手作業） | BR-CART-001 の 99 → 50    | 更新済み。runtime未実行                                   | `01`〜`05`                    |
| `coverage-analysis`                                                                                                      | 範囲外                    | 未実行                                                    | -                             |
| `adversarial-review`                                                                                                     | 範囲外                    | 未実行                                                    | -                             |
| `test-case-design`                                                                                                       | 範囲外                    | 未実行                                                    | -                             |

## 機械証拠（runtime）の扱い

- 各設計Skillの `runtime_contract.py` / `workflow_runtime.py` によるMachine Runtime Input / Result / Entity、`verify_runtime_evidence` の最終gateは **実行していません**。
- 理由: 本セッションではBashの実行権限がinline `python3 -c` を拒否され、runtimeの正規入力（stdin JSON envelope、前回成果物、current Entity）も用意していません。また、依頼のshell制約は `python3 <絶対path>` 形式のみです。
- したがって、本ディレクトリの成果物は **手作業で作成した設計草案であり、runtime検証済みではありません**。`verify_runtime_evidence` が必要な場合は別セッションで実行してください。
- workflow stateは `qa.workflow_state_root` が未設定のため、helperによる永続化を行わず、本Markdownを状態表として扱います。

## 完了判定

- テスト分析〜テスト観点・条件設計: 手作業成果物は作成済み（改版後の値に更新済み）。ただしruntime gate未通過のため「機械検証済み」とは判定しない。
- 改版（BR-CART-001 99→50）: 反映済み。ただし AC-CART-001 本文との矛盾（P-20）が未解決のため、TCN-003 の期待値は A-05（BR優先）に依存する。補助文書・実装の99残存（P-21）も未解決。
- 未解決（ブロック中または保留）の項目は `05-pending-and-questions.md` に一覧化。
- ワークフロー全体（テストケース、実行、報告）は範囲外のため未完了。
