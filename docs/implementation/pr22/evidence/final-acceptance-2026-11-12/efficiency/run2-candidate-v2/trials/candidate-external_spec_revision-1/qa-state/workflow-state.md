# QAワークフロー状態: カート機能

- Skill + 対象 / 実行範囲: `qa-workflow` + カート機能 / テスト分析〜テスト観点（条件）設計（改版対応）
- 最終更新: 2026-11-13
- 全体状態: **草稿作成済み・完了未判定**（決定論的runtime未実行・改版後の回答待ち）

## 入力revision

| 入力                 | revision                                                                                                                                                             | 備考                                                                               |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 製品 commit          | `2a8bcf57`                                                                                                                                                           | 依頼者指定。git参照は未実行のため実在は未検証                                      |
| 仕様（改版前）       | `features/cart.md`、BR-CART-001 の上限値 `99`                                                                                                                        | 初回作業時の版。内容ハッシュ未記録                                                 |
| 仕様（改版後・現在） | `product/docs/spec/features/cart.md`、sha256 `19635e51dbcef2551fadc5fb3b0510cc755a606d999a59c718c57f7267351f25`                                                      | `product-change-spec.diff` の適用後（BR-CART-001 の上限値 `50`）。版番号の記載なし |
| 改版差分             | `product-change-spec.diff`                                                                                                                                           | 変更は BR-CART-001 見出しのみ。本文・AC・画面状態は変更なし                        |
| 補助                 | `05_ui/validation_and_messages.md`、`03_domain/business_rules.md`、`03_domain/state_transitions.md`、`spec/unresolved-specifications.md`、`spec/known-deviations.md` | 正式仕様ではない。改版後も `99` が残る（Q-13）                                     |

## 改版の影響判断（2026-11-13）

- 変更種別: 境界値の変更（BR-CART-001 の上限 99 → 50）。規則の構造（3条件の最小値、操作全体拒否、0での削除）は不変。
- 再検証（変更あり）: RISK-CART-001（文言のみ。重要度は不変）、TR-001、TCN-001（CI03・CI04）、境界値分析の着眼点。
- 再利用（変更なし）: TR-002〜TR-014、TCN-002〜TCN-014、RISK-CART-002〜011、BR-CART-002/003、AC-CART-002/003。
- 新規の保留: Q-12（AC-CART-001 の `99` 記述が改版漏れ。BR の 50 を暫定採用）、Q-13（補助文書・周辺文書の `99` と実装の上限値が未確認）。Q-03 は上限値の食い違いを追記。
- 下流: `test-case-design` は未実行のため、無効化された TC はない。

## 実行したSkillと成果物

| 順 | Skill                                                | 扱い                                                            | 成果物                        |
| -- | ---------------------------------------------------- | --------------------------------------------------------------- | ----------------------------- |
| 1  | `qa-workflow`                                        | 開始・routing（改版対応）                                       | 本ファイル                    |
| 2  | `test-analysis`                                      | 初回: 新規作成 / 改版: 影響節を追加し、上限値関連の箇所だけ更新 | `01-test-analysis.md`         |
| 3  | 不明点・保留の整理（`question-analysis` 相当の分類） | 初回: 新規 / 改版: Q-12・Q-13 を追加、Q-03 を更新               | `02-questions-and-pending.md` |
| 4  | `test-requirement-design`                            | 初回: 新規 / 改版: TR-001 のみ更新                              | `03-test-requirements.md`     |
| 5  | `test-condition-design`                              | 初回: 新規 / 改版: TCN-001（CI03・CI04）のみ更新                | `04-test-conditions.md`       |

- `spec-analysis` は未実行。cart.md は features/** の正式仕様であり、BR/AC/UI状態を直接の Authority として扱った。Authority の正式解決（entity_ref等）は行っていない。
- 再利用: 上記の影響なし箇所（TR-002〜014、TCN-002〜014、RISK-002〜011 ほか）。
- 再実行: 上記の変更箇所のみ（手作業での局所更新。全体の再生成はしていない）。

## runtime 状態

- 本セッションでは `python3` でのスクリプト実行が可能になった。`.claude/skills/qa-workflow/scripts/workflow_runtime.py` を実行したが、正規化入力が無いため `invalid_input` で blocked。`runtime_contract.py verify_runtime_evidence` も同様に `valid=false`。
- 理由: 初回作業では runtime 用の機械入力・Entity（workflow_ref、各Skillの runtime unit）を生成していなかった。改版対応で後付けに組み立てると、担当Skillの機械証拠を作らずに「検証済み」と見せることになるため、本作業では実行していない。
- 結果: `can_complete` と `verify_runtime_evidence` の判定はできない。すべての成果物は手作業の草稿。
- 次回の対処: runtime 用の正規化入力（workflow_ref を含む）を作成してから `verify_runtime_evidence` を実行する。

## 未実行・制約

- 本ワークフローは「テスト分析〜テスト観点（条件）設計」の範囲のみ。テストケース設計以降は対象外。
- 製品コード・仕様書は変更していない（改版は `product-change-spec.diff` の適用結果を読むのみ）。
- 製品の実装上限値（50 か 99 か）は確認していない。

## ブロック中 / 保留

承認が必要な項目は `02-questions-and-pending.md` に記録し、先へ進めていません。

- ブロック中（該当条件のみ）: TCN-004-CI04（Q-11）、TCN-008-CI02 / CI03（Q-01）、TCN-003-CI03（Q-03）、TCN-005-CI07（Q-04）、TCN-013-CI03 / CI04（Q-10）、TCN-014 / TR-014（Q-02）
- 暫定採用（ブロックではない）: TCN-001-CI03 / CI04 の境界値は50を採用（Q-12）。承認前に実行の期待値として使わない。
- 全体停止: なし。Q-01・Q-02・Q-10 以外の要件は設計を進めた。

## 残存リスク（提案・未承認）

- 統合の同一トランザクション性（RISK-CART-003）
- 複数タブ・並行更新（Q-09）

## 再開点

1. `02-questions-and-pending.md` の Q-01〜Q-13 について人間の回答を得る（回答票化は `agent-answer-form` を検討可）。特に Q-12（AC-CART-001 の 99 を 50 へ改版するか）と Q-13（補助文書・実装の上限値）。
2. 回答を正式仕様へ反映する手続きは `product/docs/spec/change-process.md` に従う（本作業では仕様を変更していない）。
3. 回答後、該当TCNのブロック中を解除し、影響するテスト要求・条件のみを再検証する。
4. runtime 用の正規化入力を作成して `verify_runtime_evidence` を実施し、その結果を本ファイルへ記録する。
5. 次工程: `test-case-design`（テスト条件のうち解除済みのものから）。

## 完了判定

- テスト分析: 草稿作成済み（改版反映済み）。runtime未検証のため未完了扱い。
- テスト要求設計: 草稿作成済み（改版反映済み）。TR-014 ブロック中。
- テスト観点・条件設計: 草稿作成済み（改版反映済み）。ブロック中8件を含む。TCN-001 の境界値は Q-12 承認まで暫定。
- ワークフロー全体: 未完了（runtime検証未実行、ブロック中の解消待ち、Q-12・Q-13 未回答）。
