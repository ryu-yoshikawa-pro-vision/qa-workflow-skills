# ワークフロー状態 — カート機能 QA（テスト分析〜テスト観点・条件設計）

- 対象製品: `product/`（commit 2a8bcf57）
- 対象機能: カート（`product/docs/spec/features/cart.md`）
- 依頼範囲: テスト分析からテスト観点（条件）設計まで。製品のコード・仕様書は変更しない
- 進行モード: continuous（既定）
- 更新日: 2026-11-13

## 工程の状態

| 順 | Skill                   | 対象 / 実行範囲 | 成果物                                                                 | 状態                                                  |
| -- | ----------------------- | --------------- | ---------------------------------------------------------------------- | ----------------------------------------------------- |
| 1  | spec-analysis           | —               | `01-spec-analysis.md`                                                  | 完了（人間向け。機械証拠は未取得）                    |
| 2  | question-analysis       | —               | `02-question-analysis.md`                                              | 完了（分類）。承認待ちの正本は `pending-approvals.md` |
| 3  | （正本作成）            | 承認待ち        | `pending-approvals.md`（PA-01〜PA-13）                                 | 完了（承認待ち）                                      |
| 4  | test-analysis           | テスト分析      | `03-test-analysis.md`                                                  | 完了（人間向け。runtime 未取得）                      |
| 5  | test-requirement-design | —               | `04-test-requirements.md`（TR-001〜016）                               | 完了（人間向け。runtime 未取得）                      |
| 6  | test-condition-design   | テスト設計      | `05-test-condition-design.md`（TCN-001〜033、CI 74件: 採用49・保留25） | 完了（人間向け。runtime 未取得）                      |
| —  | coverage-analysis       | —               | —                                                                      | 未実施（依頼範囲外）                                  |
| —  | adversarial-review      | —               | —                                                                      | 未実施（依頼範囲外）                                  |
| —  | test-case-design        | —               | —                                                                      | 未実施（依頼範囲外）                                  |

## ブロック中 / 保留

- 全体ブロッカー: なし
- 承認待ち（保留）: PA-01〜PA-13（`pending-approvals.md`）
- 仕様なし（PA 未起票）: 無効SKU の表示時の扱い（`03-test-analysis.md` §8、`05-test-condition-design.md` TCN-014 CI03）

## 未完了の制約

- runtime-v2 の機械証拠（`verify_runtime_evidence` 等）は未取得。成果物は完成扱いしない
- 画面の現在挙動は未観測（`test-target-inspection` 未実施）
- `roles-and-permissions.md` と `ui-ux-contract.md` は全文未精読（カート関連行のみ）

## 再開先

1. PA-01〜PA-13 の回答を受けたら、`02-question-analysis.md` の該当行と `pending-approvals.md` を更新し、保留のTCN（`05-test-condition-design.md`）を `spec-analysis` から再検証する
2. 承認後、`coverage-analysis`（テスト設計の閉鎖性）へ進むか、ユーザーの指示を待つ

## 修正の記録（前回成果物との差分）

- `02-question-analysis.md` の「承認待ち 12件」→ PA-01〜PA-13 の13件に訂正（`pending-approvals.md` 補足）
- PA-13 は合計金額の規則のみ。テストレベルは承認事項から外し、既定（システムテスト）として扱う
