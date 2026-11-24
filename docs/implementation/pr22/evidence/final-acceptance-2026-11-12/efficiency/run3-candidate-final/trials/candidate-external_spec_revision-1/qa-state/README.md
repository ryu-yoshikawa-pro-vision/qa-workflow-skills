# QA状態: カート機能（テスト分析〜テスト観点・条件設計）

- 対象: `product/docs/spec/features/cart.md`（製品commit `2a8bcf57`、ユーザー申告。`.git`がなく検証不可）
- 実行範囲: テスト分析からテスト観点（条件）設計まで。テストケース設計・カバレッジ分析・独立レビューは範囲外
- 状態: **部分完了（ブロック中あり）**
- 機械可読の状態: `workflow-state.json`（入力のsha256、workflow_ref、再開点）

## 成果物

| 順 | ファイル                  | 内容                                                         | 状態     |
| -- | ------------------------- | ------------------------------------------------------------ | -------- |
| 1  | `01-spec-analysis.md`     | 仕様分析（SPEC / INF / UNK、情報源と正本判定）               | 完了     |
| 2  | `02-question-analysis.md` | 不明点・矛盾（ブロッカー局所4、要確認6、仮定1、提案1）       | 回答待ち |
| 3  | `03-test-analysis.md`     | テスト分析（プロダクトリスク11件、深度、技法、テストレベル） | 完了     |
| 4  | `04-test-requirements.md` | テスト要求27件（有効17、保留10）                             | 部分完了 |
| 5  | `05-test-conditions.md`   | テスト観点・条件18件、カバレッジ項目（有効TRのみ）           | 部分完了 |
| -  | `pending-approvals.md`    | 承認・回答が必要な項目の一覧                                 | 記録済み |
| -  | `workflow-state.json`     | 入力revision、状態、再開点                                   | 記録済み |

## 入力の扱い

- 製品コード・仕様書（`product/`）は変更していない
- 補助文書（`03_domain/business_rules.md`、`01_requirements/functional_requirements.md`、`12_quality/acceptance_criteria.md`など）は、正式な仕様の正本ではない（`spec/README.md`の正本一覧に含まれない）。その規則を根拠にした期待結果は保留にしている（Q-CART-01）

## 改版対応（2026-11-13）

- 入力: `product-change-spec.diff`（`features/cart.md`のBR-CART-001のみ: 上限99→50）
- 確認: 記録されたsha256と照合。`cart.md`だけが変わり、改版前の逆適用結果が記録値と一致。SRC-002〜107は変更なし
- 影響: 上限値に依存するTR-001、TCN-001・002の境界値（CI-001-01/04/07〜09、CI-002-07〜09）、RISK-001の根拠文言、SPEC-CART-001・016・INF-CART-002、補助の説明
- 変更なし: リスクレベル、TR / TCN の件数（TR 27件、有効17件、保留10件、TCN 18件）、保留TR、対象外、ブロック中の範囲
- 新規の論点: Q-CART-13（AC-CART-001本文の「99」が改版後のBR-CART-001と矛盾）。回答まではBR-CART-001（50）を根拠とし、PASS/FAILの最終判定前に確認
- 補助文書の旧値「99」（`business_rules.md`、`user_flows.md`、`validation_and_messages.md`）は未改版。正本ではないため今回は根拠にしない（Q-CART-01）
- 検証用スクリプト: `hash_inputs.py`（入力sha256の照合と、改版前cart.mdの逆適用一致の確認。改版差分の確認用）
- 未実施（従来どおり）: runtime-v2の機械検証、`test-case-design`、`coverage-analysis`、`adversarial-review`

## 再開方法

1. `pending-approvals.md`の回答・承認を受け取る
2. 回答を`02-question-analysis.md`の正規化方針に従って`SPEC` / `DECISION` / `ASM`へ正規化し、`spec-analysis`で再分析する
3. 影響するTRだけを`04`で再設計し、`05`の該当TCNを追加する
4. 入力のsha256が変わっていれば、変更された入力に依存する成果物だけを`要再検証`にする

## 既知の制約（この実行で満たしていないもの）

- runtime-v2の機械的な生成・検証（`verify_runtime_evidence`）は実行していない。上記3つのSkillは owner verifier に未登録のため、`unverified_scopes`として残る。成果物は手作業の分析である
- 製品commit `2a8bcf57`との一致は検証できていない（`.git`なし）
- `test-case-design`、`coverage-analysis`、`adversarial-review`は未実施
