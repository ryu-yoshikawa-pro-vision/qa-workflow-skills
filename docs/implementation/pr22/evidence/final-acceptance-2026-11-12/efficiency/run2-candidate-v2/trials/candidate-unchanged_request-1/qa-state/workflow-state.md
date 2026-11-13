# QAワークフロー状態: カート機能

- Skill + 対象 / 実行範囲: `qa-workflow` + カート機能 / テスト分析〜テスト観点（条件）設計
- 最終更新: 2026-11-13（再開・検証・追補）
- 全体状態: **範囲内の工程は草稿完了。承認待ちの条件はブロック中。ワークフロー完了は未判定（後述の最終gate未充足）**

## 入力revision

| 入力           | revision                                                                                                                                                                                                                                                                                                                                          | 備考                                                     |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 製品 commit    | `2a8bcf57`                                                                                                                                                                                                                                                                                                                                        | 依頼者指定。git参照は未実行のため実在は未検証            |
| 仕様           | `product/docs/spec/features/cart.md`（内容を読了）                                                                                                                                                                                                                                                                                                | 版番号の記載なし。内容ハッシュ未算出                     |
| 補助（非正式） | `03_domain/business_rules.md`、`03_domain/state_transitions.md`、`03_domain/roles_and_permissions.md`、`05_ui/validation_and_messages.md`、`05_ui/ui_specifications.md`、`spec/unresolved-specifications.md`、`spec/known-deviations.md`、`spec/features/authentication.md`、`spec/features/checkout-and-payment.md`（BR-CHECKOUT-002の存在確認） | 正式仕様ではない。補助文書の規定は期待結果の根拠にしない |

## 再開時の確認（今回）

- シェルが利用可能になったため、前回未実行だった確認を実施した。
- 前回草稿の相互参照を補助文書・正式仕様と照合し、以下を修正・追補した。
  - 商品追加: cart.md の目的に「商品追加」があるが BR / AC / 画面状態が無い → Q-12、TR-015、TCN-015 を追加（ブロック中）、RISK-CART-012 を追加。
  - ログイン失敗時のカート保持: 05_ui の `LOGIN_TRANSACTION_FAILED` にあるが cart.md に無い → Q-13（要確認。失敗系の期待結果は確定しない）。
  - authentication.md は目的文で「ゲストカート統合」を挙げるが本文に規則が無い → 01 の根拠表を修正。
  - Q-02: 補助文書では数量変更・削除は Cart / Item の Version を要求し、商品詳細からの追加は要求しないとされる。正式仕様との関係が不明なため根拠を追記。
- 前回の「runtime未実行のため完了不可」という記述は、前提を誤っていた点を訂正する。本workflowは対象scopeが0件のため、`workflow_runtime`はdispatchされない（`workflow_runtime.py`の「本Plan対象scopeがないworkflowではworkflow_runtimeをdispatchできません」）。

## 実行したSkillと成果物

| 順 | Skill                                                | 扱い                                                                                          | 成果物                        |
| -- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------- |
| 1  | `qa-workflow`                                        | 開始・routing・状態管理                                                                       | 本ファイル                    |
| 2  | `test-analysis`                                      | 草稿作成済み。再開時に RISK-CART-012、Q-12、Q-13 を追加                                       | `01-test-analysis.md`         |
| 3  | 不明点・保留の整理（`question-analysis` 相当の分類） | 草稿作成済み。Q-12、Q-13 を追加し Q-02 の根拠を追記                                           | `02-questions-and-pending.md` |
| 4  | `test-requirement-design`                            | 草稿作成済み。TR-015（ブロック中）を追加                                                      | `03-test-requirements.md`     |
| 5  | `test-condition-design`                              | 草稿作成済み。TCN-015 / TCN-015-CI01（ブロック中）を追加。集計を更新（48項目、ブロック中9件） | `04-test-conditions.md`       |

- `spec-analysis` は未実行。cart.md は features/** の正式仕様として直接の Authority に扱った。Authority の正式解決（entity_ref 等）は行っていない。
- 再利用: 前回の草稿は入力 revision が同一のため、再生成せず読み直して補正した（01〜04の全体は再生成していない）。
- 再実行: なし。

## 最終確認（自己検証・runtime gate）

- `verify_runtime_evidence`（qa-workflow の runtime_contract.py、`partial_rerun=false`、`previous_artifact_markdown=null`）: **valid=false**。理由は `missing_runtime_unit`（`qa-workflow::artifact:workflow_runtime:all`）。
- 原因: 本workflowは対象scopeが0件であり、`workflow_runtime`は設計上dispatchされない。Machine Runtime Input / Result を手作業で作ると、dispatchされていない証拠を捏造することになるため行っていない。
- 扱い: この gate は未充足として残す。ワークフロー全体は「完了」と判定しない。
- 本状態ファイル・01〜04 の内部整合（ID、追跡、集計）は手作業で確認済み。

## ブロック中 / 保留

承認が必要な項目は `02-questions-and-pending.md` に記録し、先へ進めていません。

- ブロッカー（該当条件のみ）: Q-01（TCN-008-CI02 / CI03）、Q-02（TCN-014 / TR-014）、Q-03（TCN-003-CI03）、Q-10（TCN-013-CI03 / CI04）、Q-11（TCN-004-CI04）、Q-12（TR-015 / TCN-015-CI01）
- 要確認（期待結果を確定しない）: Q-04（TCN-005-CI07 の表示具体）、Q-05（表示時の定義）、Q-13（ログイン失敗時のカート保持）
- 全体停止: なし。Q-01・Q-02・Q-10・Q-12 以外の要件は設計を進めた。

## 残存リスク（提案・未承認）

- 統合の同一トランザクション性（RISK-CART-003）
- 複数タブ・並行更新（Q-09）
- 商品追加の検証不能（RISK-CART-012、Q-12 が決まるまで）

## 再開点

1. `02-questions-and-pending.md` の Q-01〜Q-13 について人間の回答を得る（回答票化は `agent-answer-form` を検討可）。
2. 回答を正式仕様へ反映する手続きは `product/docs/spec/change-process.md` に従う（本作業では仕様を変更していない）。
3. 回答後、該当TCNのブロック中を解除し、影響するテスト要求・条件のみを再検証する。
4. 次工程: `test-case-design`（解除済みの条件から）。
5. 最終gate: 本workflowに対象scopeが無い限り runtime evidence は得られない。gate の扱い（scope 0 の完了条件）は qa-workflow 側の判断として確認が必要。

## 完了判定

- テスト分析: 草稿完了。Q-12・Q-13 を保留として記録。
- テスト要求設計: 草稿完了。TR-014・TR-015 ブロック中。
- テスト観点・条件設計: 草稿完了。ブロック中9件を含む。カバレッジ候補の閉鎖（対象外・重複・残存リスク・ブロック中）は記載済み。
- ワークフロー全体: 範囲内の工程は草稿完了。ただし `verify_runtime_evidence` が valid=false（scope 0 のため runtime unit なし）のため、完了とは判定しない。
