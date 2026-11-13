# ワークフロー状態: カート（cart）

- 対象製品: `product/`（commit 2a8bcf57）
- 対象機能: カート（`product/docs/spec/features/cart.md`）
- 依頼範囲: テスト分析からテスト観点（条件）設計まで（テスト要求・テスト条件・カバレッジ項目）
- 進行モード: continuous（既定）
- 製品コード・仕様書: 変更していない

## ワークフロー全体状態

**部分完了（ブロック中あり）**

依頼範囲の成果物は作成済み。ただし保留（承認要）の項目が残るため、該当する期待結果は未確定。

## 開始Skill / 最終Skill

- 開始Skill: `test-analysis`（対象: テスト分析）
- 最終Skill: `test-condition-design`（対象: テスト設計）
- 依頼範囲外（未実施）: `test-case-design`、`coverage-analysis`、`adversarial-review`

## Skill別の状態

| Skill                   | 対象 / 実行範囲                   | 状態                   | 成果物 / バージョン                           | ブロッカー / 備考                                                                      |
| ----------------------- | --------------------------------- | ---------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------- |
| test-analysis           | テスト分析                        | 完了                   | `01-test-analysis.md`                         | 変更差分（commit 2a8bcf57）は未提示のため機能全体を対象。machine runtime 未実行        |
| question-analysis       | -                                 | 完了（保留あり）       | `02-question-analysis.md`                     | 保留 9件（Q-01〜05, 07〜10）、仮定中 2件（Q-06, Q-11）、提案 1件（Q-12）               |
| test-requirement-design | テスト要求                        | 完了（一部ブロック中） | `03-test-requirements.md`（TR-CART-001〜019） | TR-CART-007 / 008 / 009 / 013 は一部ブロック中。machine runtime 未実行                 |
| test-condition-design   | テスト観点・条件 / カバレッジ項目 | 完了（一部保留）       | `04-test-conditions.md`（TCN-CART-001〜024）  | 保留項目を含む。技法は決定表・境界値・同値分割・状態遷移・CRUD。machine runtime 未実行 |
| test-case-design        | -                                 | 未開始（依頼範囲外）   | -                                             | 次工程                                                                                 |

## 承認が必要な保留項目（承認待ち）

承認者は製品仕様の決定者。承認まで該当期待結果は確定しない。

| ID   | 論点                                                       | 影響する条件 / TR                                       |
| ---- | ---------------------------------------------------------- | ------------------------------------------------------- |
| Q-01 | 許容上限超過分の統合（部分統合か全体除外か。許容上限の値） | TCN-CART-008 CI05、TCN-CART-009 CI06 / TR-CART-004、005 |
| Q-02 | カートバージョンの定義                                     | TCN-CART-012 CI01 / TR-CART-007                         |
| Q-03 | 価格変更の承認（ゲストの扱い、承認後の価格）               | TCN-CART-014 CI04〜05 / TR-CART-010                     |
| Q-04 | 数量の不正入力（非数値・負数・小数・空）                   | TCN-CART-007 CI01〜04 / TR-CART-009                     |
| Q-05 | 在庫減少後に既存数量が在庫数を超えた場合                   | TCN-CART-017 CI02 / TR-CART-013                         |
| Q-07 | 空のゲストカート・会員カート未存在での統合                 | TCN-CART-013 / TR-CART-008                              |
| Q-08 | 問題種別ごとの解消操作                                     | TCN-CART-018 CI02〜03 / TR-CART-014                     |
| Q-09 | 除外理由が複数同時に該当する場合の表示                     | TCN-CART-010 CI02 / TR-CART-005                         |
| Q-10 | 合計金額の計算規則                                         | TCN-CART-021 / TR-CART-016                              |

仮定中（承認待ち。仮定を置いて先へ進めている）:

| ID   | 仮定                                                                     |
| ---- | ------------------------------------------------------------------------ |
| Q-06 | 統合規則の正本は cart.md                                                 |
| Q-11 | 二重実行は「同一操作が二重に反映されない」という結果だけを期待結果とする |

提案（承認不要・任意）: Q-12（「チェックアウト開始時」の定義。既存表現の範囲で扱っている）

## 再開方法

次に再開する場合は、承認済みの保留項目を `02-question-analysis.md` で反映し、該当するTR / TCNを更新してから `test-case-design` へ進む。承認前にTC化する場合は、保留項目を期待結果として確定させないこと（`04-test-conditions.md` の「次工程への引継ぎ」を参照）。

## 残存する制約（機械検証）

- `test-analysis`、`test-requirement-design`、`test-condition-design` の決定論的runtime dispatch（`requirement_structure` / `condition_structure` / 各技法runtime / `materialize_coverage`）と最終 `verify_runtime_evidence` gate は**実行していない**。runtime入力の正規化形式を確認しきれず、機械証拠を手組みしないため。
- そのため、本workflowの成果物は人間向けの定義として扱い、機械検証済みとはしない。
- 観測手段（統合元カートの状態、カートバージョン値など）は未設計（test-architecture-design の範囲）。
