# ワークフロー状態: カート（`features/cart.md`）

- 対象: カート機能のQA設計（テスト分析 → テスト要求 → テスト観点・条件）
- 実行範囲: テスト分析からテスト観点（条件）設計まで。テストケース設計・カバレッジ分析・独立レビューは範囲外
- 製品: `product/`、commit `2a8bcf57`（宣言値。workspaceはgit管理外のため未検証）
- 進行モード: `continuous`（既定。`gated`の指定なし）
- 機械runtime: 未実行（`workflow_ref`なし。手動成果物として扱う）

## 中断・再開

- 前回の作業は途中で中断。再開時に `qa-state/` の既存成果物を確認した
- 2026-11-13 に `input-revisions.json` の13件のsha256を再照合 → 全件一致（変更なし）
- 再利用: `01-spec-analysis.md`、`02-question-analysis.md`（入力revisionが現在と同一のため再生成していない）
- 不足していた成果物: `02-question-analysis.md` が参照する `pending-approvals.md` が未作成だったため、今回作成した

## 工程の状態

| 工程             | Skill                     | 状態                                 | 成果物                    |
| ---------------- | ------------------------- | ------------------------------------ | ------------------------- |
| 仕様分析         | `spec-analysis`           | 完了（再利用）                       | `01-spec-analysis.md`     |
| 不明点分析       | `question-analysis`       | 完了（再利用）                       | `02-question-analysis.md` |
| 保留の記録       | —                         | 完了（今回作成）                     | `pending-approvals.md`    |
| テスト分析       | `test-analysis`           | 完了（今回作成）                     | `03-test-analysis.md`     |
| テスト要求       | `test-requirement-design` | 完了（今回作成）。TR-014はブロック中 | `04-test-requirements.md` |
| テスト観点・条件 | `test-condition-design`   | 完了（今回作成）。一部ブロック中     | `05-test-conditions.md`   |
| テストケース設計 | `test-case-design`        | 範囲外（未実施）                     | —                         |
| カバレッジ分析   | `coverage-analysis`       | 範囲外（未実施）                     | —                         |
| 独立レビュー     | `adversarial-review`      | 範囲外（未実施）                     | —                         |

## 完了判定

- 要求範囲（テスト分析〜テスト観点・条件設計）: 部分完了（ブロック中あり）
- ブロック中（局所）: Q-01, Q-02, Q-04, Q-05 ほか。範囲は `pending-approvals.md` の P-xx、A-xx に対応
- 承認待ち（仮定）: A-02（二重実行の期待結果）、A-03（異なるSKUの扱い）、A-04（統合上限）、A-05（非顧客のログイン時）
- 権威判定待ち: A-01（`business_rules.md` / `acceptance_criteria.md` の権威）。現時点ではINFとして候補扱い

## 再開先

- 回答を受けたら、該当する保留の再開先へ戻る（`pending-approvals.md` の「再開先」列を参照）
- 仕様判断（P-01〜P-13）の回答後は、`spec-analysis` → `test-requirement-design` / `test-condition-design` の順で影響範囲だけを更新する
- 上流（仕様）が変わったら、影響するTR / TCNだけを要再検証に戻す

## 次に進めるとき

- テストケース設計（`test-case-design`）は、ブロック中でないTCNから着手できる（例: TCN-001, TCN-003, TCN-004, TCN-006-CI01/CI02, TCN-007-CI01/CI02/CI05, TCN-010-CI01〜CI05, TCN-013, TCN-014-CI01/CI02）
- coverage-analysis と adversarial-review は、テストケース設計の後に実施する
