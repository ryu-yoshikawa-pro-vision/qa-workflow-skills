# ワークフロー状態: カート機能（SCREEN-STOREFRONT-CART / BR-CART / AC-CART）

- 対象: `product/docs/spec/features/cart.md`（製品commit 2a8bcf57 はユーザー申告。製品ディレクトリはgitリポジトリではなく検証不能）
- 実行範囲: テスト分析からテスト観点（条件）設計まで（spec-analysis 以降 → test-condition-design）
- 製品コード・仕様書: 変更していない（読み取りのみ）
- 承認状態: 質問はすべて未承認。承認済みの仮定はない

## 工程の状態

| 順 | 工程（Skill）           | 成果物                    | 状態                     | 備考                                                     |
| -- | ----------------------- | ------------------------- | ------------------------ | -------------------------------------------------------- |
| 1  | spec-analysis           | `01-spec-analysis.md`     | 完了（前回実施・再利用） | 入力revisionが現在と一致したため再生成していない         |
| 2  | question-analysis       | `02-question-analysis.md` | 完了（今回作成）         | Q-CART-001〜012。ブロッカー4件、要確認4件、提案・任意3件 |
| 3  | test-analysis           | `03-test-analysis.md`     | 完了（今回作成）         | プロダクトリスク RK-CART-01〜11                          |
| 4  | test-requirement-design | `04-test-requirements.md` | 完了（今回作成）         | TR-CART-001〜025（確定14 / 保留9 / 対象外2）             |
| 5  | test-condition-design   | `05-test-conditions.md`   | 完了（今回作成）         | COV-CART-001〜046（保留依存の項目は残す）                |

## 再開の記録

- 再開: 前回の中断後、`qa-state/` に残っていた `01-spec-analysis.md` と `input-revisions.json` を確認。
- 入力revisionの確認: `qa-state/tools/input_revisions.py`（書き込みなし）で14件すべてのsha256が記録と一致。`01-spec-analysis.md` は再利用し、再生成していない。
- `input-revisions.json` は更新していない（一致していたため）。

## 承認待ち（保留として記録）

| 質問ID     | 分類       | 保留にしている期待結果                                                           |
| ---------- | ---------- | -------------------------------------------------------------------------------- |
| Q-CART-001 | ブロッカー | 数量 > 現在在庫など、4種以外の再検証問題                                         |
| Q-CART-002 | ブロッカー | 価格変更の承認の操作・記録、承認前後のチェックアウト可否                         |
| Q-CART-003 | ブロッカー | 統合時の除外理由の表示内容                                                       |
| Q-CART-005 | ブロッカー | 現在価格・合計金額の数値                                                         |
| Q-CART-004 | 要確認     | サインアップ時の統合                                                             |
| Q-CART-006 | 要確認     | 更新中の二重実行防止、カートバージョンの増分規則（DEC-001 の現在有効性も未確認） |
| Q-CART-008 | 要確認     | 数量の負数・小数・非数値                                                         |
| Q-CART-011 | 要確認     | 複数明細の一括操作での拒否範囲、empty状態のオラクル                              |

提案・任意（期待結果の根拠にしない）: Q-CART-007（絶対数量指定）、Q-CART-010（表示順）、Q-CART-012（ロール境界の補足）。

## 未実施・制約

- adversarial-review、coverage-analysis（追跡の独立確認）は未実施。今回の範囲外、または後続工程。
- test-case-design、test-execution は今回の範囲外。
- `authority_entities.py` 等の機械証拠（runtime）は未実行。
- 非正本（`docs/03_domain/business_rules.md`、`docs/01_requirements/functional_requirements.md`）の内容は期待結果の根拠にしていない。
- DEC-001（D-010）のステータスは未確認。

## 次の一手（承認後）

1. Q-CART-001〜008, 011 の回答を得る（仕様担当者）。回答は `qa-state/02-question-analysis.md` の承認状態へ反映する。
2. 回答後、影響する TR / COV だけを `要再検証` として再確認する（05 の保留項目）。
3. test-case-design へ進む（確定条件から着手可能）。
