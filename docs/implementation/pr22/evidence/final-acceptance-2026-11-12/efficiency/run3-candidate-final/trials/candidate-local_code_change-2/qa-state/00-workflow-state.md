# QAワークフロー状態: カート（Cart）

## 要求

- 対象: カート機能（`product/docs/spec/features/cart.md`）
- 実施範囲: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ基準・項目）設計まで
- 除外: テストケース詳細化（`test-case-design`）、カバレッジ分析（`coverage-analysis`）、独立レビュー（`adversarial-review`）、テスト実行、製品コード・仕様書の変更
- 承認が必要な項目: `05-pending-and-questions.md` に保留として記録（先へ進めていない）

## 入力revision

| 項目                                                                                                                                                                          | 値                                                                                                        | 確認状況                                                              |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 製品commit                                                                                                                                                                    | `2a8bcf57`（依頼者の指定）                                                                                | `product/` に `.git` が存在しないため、本セッションでは検証していない |
| ローカル製品差分 `product-change-code.diff`                                                                                                                                   | sha256 `dd092337…b0bf`（275 bytes）。`src/application/contracts/common.ts` に `maxCartQuantity: 99 → 100` | 2026-11-13 に計算済み。製品commitには含まれない局所変更               |
| `src/application/contracts/common.ts`（差分適用後）                                                                                                                           | sha256 `7fece7dd…7932`                                                                                    | 計算済み                                                              |
| `src/domain/services/cart.ts`（上限判定の実体）                                                                                                                               | sha256 `fca912a8…d1c0`。`CART_QUANTITY_LIMIT = 99`                                                        | 計算済み・未変更                                                      |
| `docs/spec/features/cart.md`                                                                                                                                                  | sha256 `385777e5…7216`（5308 bytes）                                                                      | 計算済み。2026-11-13 の再計算で前回値と一致（仕様は未変更）           |
| `docs/04_data/application_contracts.md`                                                                                                                                       | sha256 `835e043c…3ffb`（53266 bytes）。`maxCartQuantity: 99`                                              | 計算済み・未変更（差分と不一致）                                      |
| 関連仕様（README, product-scope, roles-and-permissions, state-and-scenarios, unresolved-specifications, known-deviations, storefront, checkout-and-payment, native-customer） | 指紋は計算済み（同じ計算結果は本セッションの作業記録に残る）                                              | 参照のみ                                                              |
| 案件Project Context（QA用）                                                                                                                                                   | 未発見。`product/docs/PROJECT_CONTEXT.md` は製品開発用の運用文書で、QA案件のProject Contextではない       | `project-context` は未実行                                            |
| 既存QA成果物                                                                                                                                                                  | なし（`qa-state/` は空）                                                                                  | 再利用対象なし                                                        |

## Skill実行状態

| Skill                     | 対象 / 実行範囲           | 状態                                     | 成果物                        |
| ------------------------- | ------------------------- | ---------------------------------------- | ----------------------------- |
| `spec-analysis`           | カート（BR/AC/画面状態）  | 完了（手作業、runtimeなし）              | `01-spec-authority.md`        |
| `question-analysis`       | 仕様の曖昧さ・欠落の分類  | 完了（分類のみ、正式な回答収集は未実施） | `05-pending-and-questions.md` |
| `test-analysis`           | `テスト分析`              | 完了（手作業、runtime未実行）            | `02-test-analysis.md`         |
| `test-requirement-design` | テスト要求                | 完了（手作業、runtime未実行）            | `03-test-requirements.md`     |
| `test-condition-design`   | `テスト設計` の条件・観点 | 完了（手作業、runtime未実行）            | `04-test-conditions.md`       |
| `coverage-analysis`       | 範囲外                    | 未実行                                   | -                             |
| `adversarial-review`      | 範囲外                    | 未実行                                   | -                             |
| `test-case-design`        | 範囲外                    | 未実行                                   | -                             |

## 変更の記録と影響判定（2026-11-13）

| 項目             | 内容                                                                                                                                                                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 変更             | `src/application/contracts/common.ts` の `maxCartQuantity` を `99` から `100` へ変更（局所差分）                                                                                                                                      |
| 仕様への影響     | **仕様は未変更**（`cart.md` の sha256 は前回と一致）。BR-CART-001 / AC-CART-001 は「99」のまま。仕様の意味が変わらないため、既存の要求・観点・条件・期待値を `要再検証` へ戻す対象はなし                                              |
| 実行時の挙動     | **変化なし**。上限判定の実体は `src/domain/services/cart.ts` の `CART_QUANTITY_LIMIT = 99`（`maximumCartQuantity` から使用）。DB制約も `quantity BETWEEN 1 AND 99`。`maxCartQuantity` は `src` 内で参照されていない                   |
| 問題             | 差分は**仕様と矛盾する定数**。`application_contracts.md`（99）、`cart.md`（99）、domain（99）、DB制約（99）と不一致になった。将来 `maxCartQuantity` を参照する箇所が追加されると、UIが100を受理し、DB制約で保存失敗する不整合が起きる |
| 扱い             | `change-process.md`「既存仕様への違反」に従い、仕様を実装に合わせて書き換えない。100が意図した変更かの判断は仕様責任者へ回す（`P-20`）。QAの期待値は99のまま。100を根拠にしない                                                       |
| 追加の提案       | 契約定数と仕様・domain・DB制約の一致を固定する非E2Eテストの追加（`P-21`、承認待ち）                                                                                                                                                   |
| 既存期待値の変更 | なし（TCN-001〜003 等の境界は99で維持）                                                                                                                                                                                               |
| 再利用 / 再実行  | 既存の観点・条件・要求はすべて再利用。再生成なし                                                                                                                                                                                      |

## 機械証拠（runtime）の扱い

- 各設計Skillの `runtime_contract.py` / `workflow_runtime.py` によるMachine Runtime Input / Result / Entity、`verify_runtime_evidence` の最終gateは **今回の変更でも実行していません**。今回はowner scopeの再dispatchが不要（仕様の意味が不変）で、かつ `qa.workflow_state_root` が未設定のため永続化できないためです（`P-17` / `P-18`）。
- 理由: 本セッションではBashの実行権限がinline `python3 -c` を拒否され、runtimeの正規入力（stdin JSON envelope、前回成果物、current Entity）も用意していません。また、依頼のshell制約は `python3 <絶対path>` 形式のみです。
- したがって、本ディレクトリの成果物は **手作業で作成した設計草案であり、runtime検証済みではありません**。`verify_runtime_evidence` が必要な場合は別セッションで実行してください。
- workflow stateは `qa.workflow_state_root` が未設定のため、helperによる永続化を行わず、本Markdownを状態表として扱います。

## 完了判定

- テスト分析〜テスト観点・条件設計: 手作業成果物は作成済み。ただしruntime gate未通過のため「機械検証済み」とは判定しない。
- 未解決（ブロック中または保留）の項目は `05-pending-and-questions.md` に一覧化。
- ワークフロー全体（テストケース、実行、報告）は範囲外のため未完了。
