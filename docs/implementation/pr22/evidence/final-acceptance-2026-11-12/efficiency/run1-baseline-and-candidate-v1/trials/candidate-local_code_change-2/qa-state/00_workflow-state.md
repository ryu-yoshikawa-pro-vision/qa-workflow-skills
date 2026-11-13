# QAワークフロー状態: カート

- 対象: `product/docs/spec/features/cart.md`（SCREEN-STOREFRONT-CART、BR-CART-001〜003、AC-CART-001〜003）
- 対象製品: `product/`（commit 2a8bcf57、利用者申告。git管理外のため未照合）
- 実施範囲: テスト分析 → テスト要求 → テスト観点・条件設計（テストケース設計以降は対象外）
- 製品コード・仕様書: 変更なし
- 更新日: 2026-11-13

## 工程状態

| 順序 | Skill                                            | 成果物                                                                                                                                          | 状態                      | 備考                                                                                       |
| ---: | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------ |
|    1 | feature-analysis / spec-analysis（情報源の確認） | 本文は作らず、cart.md と business_rules.md §3、acceptance_criteria.md §4、state-and-scenarios.md、roles-and-permissions.md を採用根拠として確認 | 完了（手動確認）          | 既存の機能ID・Authority正本の再作成は行っていない。`feature-analysis`の正式runtimeは未実行 |
|    2 | question-analysis                                | `02_question-log.md`                                                                                                                            | 完了。保留5件             | Q-01, Q-03, Q-04, Q-05, Q-08 が承認待ち                                                    |
|    3 | test-analysis                                    | `01_test-analysis.md`                                                                                                                           | 完了（草案）              | runtime evidence（`verify_runtime_evidence`）未実施                                        |
|    4 | test-requirement-design                          | `03_test-requirements.md`                                                                                                                       | 完了（草案）              | TR-CART-01〜18。TR-05, 18 は保留を含む                                                     |
|    5 | test-condition-design                            | `04_test-conditions.md`                                                                                                                         | 完了（草案）              | CND-CART-001〜064。保留条件あり                                                            |
|    – | coverage-analysis                                | 未実施                                                                                                                                          | 対象外（工程6以降に相当） | TC化後に実施                                                                               |
|    – | test-case-design / test-execution                | 未実施                                                                                                                                          | 対象外                    | 指示範囲外                                                                                 |

## 保留（承認・回答待ち）

| ID   | 保留内容                                                      | 止めている範囲                                                                                  | 回答者                              |
| ---- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------- |
| Q-01 | Android（Native）を対象に含めるか                             | TR-12 の android 観点、TR-18、CND-053                                                           | ユーザー / 案件責任者               |
| Q-03 | 価格改定の承認UI                                              | CND-042 の承認操作、TR-06 のUI部分                                                              | 仕様責任者                          |
| Q-04 | 追加操作の数量0・負数・非整数                                 | CND-014                                                                                         | 仕様責任者                          |
| Q-05 | 古いVersionの変更操作の挙動（拒否表示・状態）                 | CND-017, 018、TR-05                                                                             | 仕様責任者                          |
| Q-08 | 合計金額の丸め規則                                            | CND-064、TR-15 の端数                                                                           | 仕様責任者（pricing）               |
| Q-16 | カート上限を99から100へ変更する意図（製品差分と仕様の不一致） | 現時点の期待は仕様どおり99で確定。100を採用する場合のみ CND-CART-001〜007、TR-01〜03 を要再検証 | 仕様責任者（cart 担当）・製品開発者 |

仮定で継続中（承認待ち）: Q-02（会員ランクを再検証対象に含める）、Q-06（二重実行は観測結果のみで判定）、Q-07（統合時の通知は表示されればよい）、Q-09（空カートの導線先は商品一覧系）、Q-10（既定のリスクマトリクスを使用）。

## 変更履歴

- 2026-11-13: `product-change-code.diff` を取り込み。内容は `src/application/contracts/common.ts` の `maxCartQuantity` を 99 → 100 に変更する1箇所だけ（製品コード変更、仕様・QA成果物の既存本文は変更なし）。
  - 影響判断: 実カート判定は `src/domain/services/cart.ts` の `CART_QUANTITY_LIMIT = 99` を使用し、`maxCartQuantity` の参照箇所は確認できなかった。実行時の上限は変わらないため、既存のTR / CND の期待結果（99）は維持する。
  - 仕様（cart.md BR-CART-001、AC-CART-001、business_rules L137、`application_contracts.md`）は99のままで、製品差分はそれと不一致。製品コードの変更を仕様の代わりとは扱わず、Q-16として仕様責任者へ判断を依頼した。
  - 再検証で `要再検証` にしたものはない。01（変更/影響マップ）と02（Q-16）だけを更新。03 / 04 は変更なし。
  - 残存の検証上の意味: CND-CART-006（99受理 / 100拒否）は、将来 `maxCartQuantity` が判定へ接続された場合の検出条件として機能する。

## 検証の追加注記（今回の更新）

- 今回も決定論的runtime（`verify_runtime_evidence`）は実行していない。成果物は引き続き「草案・未検証」。

## 検証状態（重要）

- 本ワークフローは決定論的runtime（`scripts/runtime_contract.py`、`workflow_runtime.py`等）を実行していません。`verify_runtime_evidence`の `valid=true` は得ていないため、成果物は「草案・未検証」です。完成扱いしません。
- 各成果物は仕様本文と突き合わせて手作業で作成しています。仕様の転記は確認していますが、runtime生成の機械証拠は付いていません。
- 外部サービス（Claude Docs / Data 等）は利用していません。

## 再開方法

1. Q-01, Q-03, Q-04, Q-05, Q-08, Q-16 の回答を受けたら（Q-16で100が正と決まった場合は、BR / AC の改定を先に行い、CND-CART-001〜007 と TR-CART-01〜03 を要再検証にする） `02_question-log.md` の該当行を更新し、`04_test-conditions.md` の保留条件を確定させる。
2. 仮定（Q-02, 06, 07, 09, 10）の承認・却下を受けたら、TR / CND の「仮定」表記を更新する。
3. 回答後に `test-requirement-design` と `test-condition-design` を再確認する。上流（仕様・Q）の変更で影響するのは保留に依存する TR / CND だけ。
4. 次工程: `test-case-design`（保留が解消した範囲から着手可能）。

## 再利用できる成果物

- 上記5ファイル（`00`〜`04`）を再利用可能。仕様 `cart.md` が変わった場合は、BR / AC 参照を持つ TR と CND を `要再検証` として扱う。
