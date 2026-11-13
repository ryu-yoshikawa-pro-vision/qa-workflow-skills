# ワークフロー状態 — カート機能QA（テスト分析からテスト観点（条件）設計まで）

- 要求: カート機能（`product/docs/spec/features/cart.md`）のQA。実施範囲はテスト分析からテスト観点（条件）設計まで
- 実施モード: 製品・仕様書は変更しない。承認が必要な項目は保留として記録し、先へ進めない
- 最終工程: test-condition-design（テストケース設計・実行・E2Eは対象外）

## 入力revision

製品 `product/` に `.git` がなく、依頼文の commit 2a8bcf57 は照合できません。以下は `product/docs/spec/` の内容ハッシュ（SHA-256先頭16桁・バイト数）で記録します。

| 入力                                                 | ハッシュ         | バイト数 |
| ---------------------------------------------------- | ---------------- | -------- |
| features/cart.md（SRC-01 Authority）                 | 385777e56a0d1c7f | 5308     |
| state-and-scenarios.md（SRC-03）                     | ccd0cab4b0bd156e | 4140     |
| roles-and-permissions.md（SRC-02）                   | 519731749c55d9e0 | 3833     |
| product-scope.md（SRC-05）                           | 23508ebe243d011e | 8455     |
| features/checkout-and-payment.md（境界参照・他機能） | 9877302a255eb33e | 13031    |
| features/authentication.md（SRC-08・他機能）         | 3334ecd7b5fb00c6 | 7052     |
| features/storefront.md（SRC-06・他機能）             | 3f77926ad16369ea | 12935    |
| unresolved-specifications.md（SRC-09）               | c3ac09d0f145d973 | 1076     |
| known-deviations.md（SRC-10）                        | 518d110c069d82bb | 538      |
| ui-ux-contract.md（SRC-04）                          | ac9b86d99ff6cf1b | 3925     |

commit 2a8bcf57 との照合: **不可**（ハッシュは内容の記録であり、commitの同一性は証明しない）。

## 工程の状態

| 順 | Skill                   | 成果物                    | 状態                   | 再利用 / 再実行                                                                          | 備考                                                                        |
| -- | ----------------------- | ------------------------- | ---------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| 1  | spec-analysis           | `01-spec-authority.md`    | 完了（再利用）         | 前回成果物を本回で `cart.md` と照合し、BR / AC / 状態 / 画面表の参照が一致したため再利用 | 前回の入力revision記録がなかったため、本回の内容ハッシュを初めて記録        |
| 2  | question-analysis       | `02-questions.md`         | 完了（再利用）         | 01 と同じ照合。PEND-01〜09 は現在も有効                                                  | 局所保留。ブロッカー0件                                                     |
| 3  | test-analysis           | `03-test-analysis.md`     | 完了（本回で新規作成） | —                                                                                        | 前回中断点。RISK-001〜007、テストレベルはシステム（既定）                   |
| 4  | test-requirement-design | `04-test-requirements.md` | 完了（本回で新規作成） | —                                                                                        | TR-001〜018。TR-008 はカートバージョンとして `02-questions.md` の参照と一致 |
| 5  | test-condition-design   | `05-test-conditions.md`   | 完了（本回で新規作成） | —                                                                                        | TCN-001〜049（欠番あり）。TR-008・TR-013 は全保留                           |

前回の `02-questions.md` が参照していた `05-test-conditions.md` は存在しなかったため、本回で新規作成した。

## 停止・保留

- ブロッカー: なし（全体停止なし）
- 保留（承認・製品判断待ち）: PEND-01〜09 と追加1件（`05-test-conditions.md` の「保留まとめ」を正本とする）
- 保留の解除には製品ownerの回答が必要。回答後は `spec-analysis` で DEC / ASM 化し、影響するTCNだけを `要再検証` とする

## 未検証・未完了の範囲

- `test-analysis` / `test-requirement-design` / `test-condition-design` の runtime dispatch は実施していない（この作業ディレクトリに runtime-v2 の状態がなく、owner verifier は本workflowに登録されていない）。成果物は手作業で作成し、machine evidence は持たない
- `unverified_scopes`: test-analysis、test-requirement-design、test-condition-design（いずれも完了扱いにしない）
- 観測手段の未確定: 統合元ゲストカートの abandoned（TR-006）、カートバージョン（TR-008）は UI から観測できない可能性があり、test-architecture-design で決定が必要
- commit 2a8bcf57 との照合は未実施（`.git` なし）

## 次の再開点

1. 製品ownerへ保留 PEND-01〜09 を提示（回答形式が必要なら `agent-answer-form` で質問票化できる）
2. 回答を受けたら `spec-analysis` → 影響するTR / TCN のみ `要再検証`
3. 観測方法の決定のため `test-architecture-design`（TR-006 / TR-008）
4. 次工程（テストケース化 `test-case-design`）は本依頼の範囲外のため未実施

## 中断・再開の記録

- 前回: spec-analysis・question-analysis まで完了し、test-analysis 以降は未着手（workflow stateが存在しなかったため、中断時点は成果物から推定）
- 本回: 上記の再利用判定の後、test-analysis から test-condition-design まで実施
