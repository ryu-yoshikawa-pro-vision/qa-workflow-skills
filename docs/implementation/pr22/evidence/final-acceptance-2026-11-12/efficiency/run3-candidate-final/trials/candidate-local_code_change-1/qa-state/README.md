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

## 再開方法

1. `pending-approvals.md`の回答・承認を受け取る
2. 回答を`02-question-analysis.md`の正規化方針に従って`SPEC` / `DECISION` / `ASM`へ正規化し、`spec-analysis`で再分析する
3. 影響するTRだけを`04`で再設計し、`05`の該当TCNを追加する
4. 入力のsha256が変わっていれば、変更された入力に依存する成果物だけを`要再検証`にする

## 製品変更の影響確認（2026-11-13）

- 入力: `product-change-code.diff`（`src/application/contracts/common.ts` の `maxCartQuantity` を 99 → 100）
- 仕様入力（SRC-001〜SRC-107b）のsha256は全件一致。仕様は変更されていない
- 判断: 仕様の意味は変わらないため、`01`〜`05`は再生成せず再利用する。下流の`要再検証`はなし
- 矛盾: 仕様・ドメイン定数（`CART_QUANTITY_LIMIT = 99`）・DB CHECK・`docs/04_data/application_contracts.md`は99で、変更された定数だけが100。`src`内で`maxCartQuantity`を参照する箇所は見つからず、実効値への影響は確認できていない
- 扱い: 期待結果は仕様の99に従う。仕様と製品の意図の確認は保留事項 P-06（`pending-approvals.md`）。実行段階で100が受け入れられた場合は欠陥候補として扱う（ここでは判定しない）
- 詳細: `workflow-state.json` の `product_local_change_review`

## 既知の制約（この実行で満たしていないもの）

- runtime-v2の機械的な生成・検証（`verify_runtime_evidence`）は実行していない。上記3つのSkillは owner verifier に未登録のため、`unverified_scopes`として残る。成果物は手作業の分析である
- 製品commit `2a8bcf57`との一致は検証できていない（`.git`なし）
- `test-case-design`、`coverage-analysis`、`adversarial-review`は未実施
