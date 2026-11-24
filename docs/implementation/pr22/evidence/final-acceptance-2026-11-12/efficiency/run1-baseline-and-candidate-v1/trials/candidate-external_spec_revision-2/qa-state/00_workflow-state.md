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

| ID   | 保留内容                                      | 止めている範囲                        | 回答者                |
| ---- | --------------------------------------------- | ------------------------------------- | --------------------- |
| Q-01 | Android（Native）を対象に含めるか             | TR-12 の android 観点、TR-18、CND-053 | ユーザー / 案件責任者 |
| Q-03 | 価格改定の承認UI                              | CND-042 の承認操作、TR-06 のUI部分    | 仕様責任者            |
| Q-04 | 追加操作の数量0・負数・非整数                 | CND-014                               | 仕様責任者            |
| Q-05 | 古いVersionの変更操作の挙動（拒否表示・状態） | CND-017, 018、TR-05                   | 仕様責任者            |
| Q-08 | 合計金額の丸め規則                            | CND-064、TR-15 の端数                 | 仕様責任者（pricing） |

仮定で継続中（承認待ち）: Q-02（会員ランクを再検証対象に含める）、Q-06（二重実行は観測結果のみで判定）、Q-07（統合時の通知は表示されればよい）、Q-09（空カートの導線先は商品一覧系）、Q-10（既定のリスクマトリクスを使用）、Q-16（数量上限は50を採用、下記改版対応）。

## 改版対応（2026-11-13、`product-change-spec.diff`）

- 変更内容: `cart.md` BR-CART-001 の上限値のみ 99 → 50（diffは1 hunk、1行）。他の BR / AC / 画面状態・機能一覧の変更はなし。
- 影響判断: 上流（仕様）の変更は BR-CART-001 の上限値だけ。下流のうち上限値に依存する箇所だけを更新した。
  - `01_test-analysis.md`: 変更/影響マップ（数量上限行）、RISK-CART-01（99の境界→50の境界）、テスト技法（L = min(S, P, 50)）を更新。リスクレベル（高）と他リスクは不変。
  - `03_test-requirements.md`: TR-CART-01 の上限値を50へ。TR-02、TR-03、TR-04以降は上限値を直接参照しないため変更なし。
  - `04_test-conditions.md`: L の定義、CND-CART-004（S < 50）、CND-CART-006（50 / 51、旧99残存の検出を追加）。CND-001〜003、005、007〜014は L 参照のみで変更なし。
  - `02_question-log.md`: Q-16 を追加（仮定可能・矛盾）。
- 未解決の矛盾（Q-16、承認待ち）: 改版後も `cart.md` AC-CART-001（L74 "99"）、`product/docs/03_domain/business_rules.md` L137（"上限値99"）が99のまま。製品側は `cart.ts` L3 / `common.ts` L97 / DB CHECK が99。仮定として50を採用したが、AC と business_rules の改版を仕様責任者が確認するまで、上限値の期待結果は確定扱いにしない。
- 製品・仕様書: 変更なし。製品実装は依然99のため、50を期待する条件は現行実装で不一致になり得る（欠陥候補、defect-managementで後段扱い。本対応では判定しない）。
- 未実施: 決定論的runtime（`verify_runtime_evidence`等）は従来どおり未実施。本改版の反映も手作業の草案更新であり、runtime証拠は付いていない。
- 次の判断: 仕様責任者が Q-16 を回答したら、AC-CART-001 / business_rules の確定値に合わせて TR-CART-01 と CND-004 / 006 の50を確定または差し替える。

## 検証状態（重要）

- 本ワークフローは決定論的runtime（`scripts/runtime_contract.py`、`workflow_runtime.py`等）を実行していません。`verify_runtime_evidence`の `valid=true` は得ていないため、成果物は「草案・未検証」です。完成扱いしません。
- 各成果物は仕様本文と突き合わせて手作業で作成しています。仕様の転記は確認していますが、runtime生成の機械証拠は付いていません。
- 外部サービス（Claude Docs / Data 等）は利用していません。

## 再開方法

1. Q-01, Q-03, Q-04, Q-05, Q-08 の回答を受けたら `02_question-log.md` の該当行を更新し、`04_test-conditions.md` の保留条件を確定させる。
2. 仮定（Q-02, 06, 07, 09, 10）の承認・却下を受けたら、TR / CND の「仮定」表記を更新する。
3. 回答後に `test-requirement-design` と `test-condition-design` を再確認する。上流（仕様・Q）の変更で影響するのは保留に依存する TR / CND だけ。
4. 次工程: `test-case-design`（保留が解消した範囲から着手可能）。

## 再利用できる成果物

- 上記5ファイル（`00`〜`04`）を再利用可能。仕様 `cart.md` が変わった場合は、BR / AC 参照を持つ TR と CND を `要再検証` として扱う。
