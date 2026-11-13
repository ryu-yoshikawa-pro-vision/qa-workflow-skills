# QAワークフロー状態: カート機能

- Skill + 対象 / 実行範囲: `qa-workflow` + カート機能 / テスト分析〜テスト観点（条件）設計
- 最終更新: 2026-11-13
- 全体状態: **草稿作成済み・完了未判定**（決定論的runtimeおよびverify未実行のため）

## 入力revision

| 入力        | revision                                                                                                                                                             | 備考                                                                                                           |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 製品 commit | `2a8bcf57`                                                                                                                                                           | 依頼者指定。git参照は未実行のため実在は未検証                                                                  |
| 仕様        | `product/docs/spec/features/cart.md`（ファイル内容を読了）                                                                                                           | 版番号の記載なし。内容ハッシュ未算出                                                                           |
| 補助        | `03_domain/business_rules.md`、`03_domain/state_transitions.md`、`05_ui/validation_and_messages.md`、`spec/unresolved-specifications.md`、`spec/known-deviations.md` | 正式仕様ではない。未確定事項・既知の差異は「有効な項目なし」（known-deviations）/ カート関連なし（unresolved） |

## 実行したSkillと成果物

| 順 | Skill                                                | 扱い                       | 成果物                        |
| -- | ---------------------------------------------------- | -------------------------- | ----------------------------- |
| 1  | `qa-workflow`                                        | 開始・routing              | 本ファイル                    |
| 2  | `test-analysis`                                      | 新規作成（既存成果物なし） | `01-test-analysis.md`         |
| 3  | 不明点・保留の整理（`question-analysis` 相当の分類） | 新規作成                   | `02-questions-and-pending.md` |
| 4  | `test-requirement-design`                            | 新規作成                   | `03-test-requirements.md`     |
| 5  | `test-condition-design`                              | 新規作成                   | `04-test-conditions.md`       |

- `spec-analysis` は未実行。cart.md は features/** の正式仕様であり、BR/AC/UI状態を直接の Authority として扱った。Authority の正式解決（entity_ref等）は行っていない。
- 再利用: なし（`qa-state/` は作業開始時に空）。
- 再実行: なし。

## 未実行・制約

- **シェル実行不可**: 本セッションでは Bash が拒否されたため、Skill の Python runtime（`runtime_contract.py`、`workflow_runtime.py`、`verify_runtime_evidence`、`artifact_graph.py`）を一切実行していない。すべての成果物は手作業の草稿であり、Machine Runtime Input / Result / Entity は存在しない。
- 上記により、`can_complete` と `verify_runtime_evidence` の判定はできない。
- 本ワークフローは「テスト分析〜テスト観点（条件）設計」の範囲のみ。テストケース設計以降は対象外。

## ブロック中 / 保留

承認が必要な項目は `02-questions-and-pending.md` に記録し、先へ進めていません。

- ブロック中（該当条件のみ）: TCN-004-CI04（Q-11）、TCN-008-CI02 / CI03（Q-01）、TCN-003-CI03（Q-03）、TCN-005-CI07（Q-04）、TCN-013-CI03 / CI04（Q-10）、TCN-014 / TR-014（Q-02）
- 全体停止: なし。Q-01・Q-02・Q-10 以外の要件は設計を進めた。

## 残存リスク（提案・未承認）

- 統合の同一トランザクション性（RISK-CART-003）
- 複数タブ・並行更新（Q-09）

## 再開点

1. `02-questions-and-pending.md` の Q-01〜Q-11 について人間の回答を得る（回答票化は `agent-answer-form` を検討可）。
2. 回答を正式仕様へ反映する手続きは `product/docs/spec/change-process.md` に従う（本作業では仕様を変更していない）。
3. 回答後、該当TCNのブロック中を解除し、影響するテスト要求・条件のみを再検証する。
4. runtime（シェル実行が可能になった後）で `verify_runtime_evidence` を実施し、その結果を本ファイルへ記録する。
5. 次工程: `test-case-design`（テスト条件のうち解除済みのものから）。

## 完了判定

- テスト分析: 草稿作成済み。runtime未検証のため未完了扱い。
- テスト要求設計: 草稿作成済み。TR-014 ブロック中。
- テスト観点・条件設計: 草稿作成済み。ブロック中8件を含む。カバレッジ候補の閉鎖（対象外・重複・残存リスク・ブロック中）は記載済み。
- ワークフロー全体: 未完了（runtime検証未実行、ブロック中の解消待ち）。
