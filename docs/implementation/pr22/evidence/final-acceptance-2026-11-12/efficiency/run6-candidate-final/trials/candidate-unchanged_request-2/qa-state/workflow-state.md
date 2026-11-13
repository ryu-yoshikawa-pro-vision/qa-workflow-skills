# ワークフロー状態: カート機能 QA（テスト分析〜テスト観点・条件設計）

- Skill: `qa-workflow`
- 対象製品: `product/`（commit 2a8bcf57）
- 対象機能: カート（`product/docs/spec/features/cart.md`）
- 実行範囲: テスト分析からテスト観点（条件）設計まで。テストケース設計・実行・E2E・Regression・欠陥管理は対象外。
- 進行モード: `continuous`（既定。依頼から gated の指定なし）
- 制約: 製品コード・仕様書は変更しない。シェルは `python3 <絶対path>` のみ使用。
- 作成日: 2026-11-13

## 工程の状態

| 順 | Skill                                      | 対象 / 実行範囲            | 状態                                 | 成果物                                            | 備考                                |
| -: | ------------------------------------------ | -------------------------- | ------------------------------------ | ------------------------------------------------- | ----------------------------------- |
|  1 | `spec-analysis`                            | 規定領域の Authority 解決  | 完了（人間可読）                     | `01-spec-analysis.md`                             | 機械証拠（entity-state-v2）は未生成 |
|  2 | `question-analysis`                        | 不明点の分類・保留化       | 完了（ブロック中あり）               | `02-question-analysis.md`、`pending-approvals.md` | ブロッカー6件（該当範囲のみ）       |
|  3 | `test-analysis`                            | 対象 `テスト分析`          | 完了（人間可読）                     | `03-test-analysis.md`                             | リスク13件、技法選定                |
|  4 | `test-requirement-design`                  | 要求                       | 完了（一部ブロック中）               | `04-test-requirements.md`                         | TR-014 ブロック中、TR-008 一部      |
|  5 | `test-condition-design`                    | 観点・条件・カバレッジ項目 | 完了（一部ブロック中）               | `05-test-conditions.md`                           | 観点11件、有効項目46、ブロック中15  |
|  - | `test-case-design`                         | -                          | 対象外（依頼範囲外）                 | -                                                 | -                                   |
|  - | `coverage-analysis` / `adversarial-review` | -                          | 未実行（依頼範囲外。必要なら後続で） | -                                                 | 閉鎖性は `05` の自己確認表のみ      |

## 再利用 / 再実行の記録

- 初回実行のため、既存の成果物はなし。`input-revisions.json` の状態は `no_record`（開始時）。
- 開始時の入力 revision を `input-revisions.json` に記録済み（対象14件、`product/docs/` 配下）。次回実行時に `input_revision.py compare` で `same` ならこの分析を再利用し、`changed` の path に依存する成果物だけを `要再検証` にする。

## 入力 revision と依存

| 成果物                    | 依存する入力（path）                                                                                                                                                                                                                                    | 再実行の条件                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `01-spec-analysis.md`     | cart.md, roles-and-permissions.md, state-and-scenarios.md, authentication.md, storefront.md, ui-ux-contract.md, product-scope.md, unresolved-specifications.md, known-deviations.md, checkout-and-payment.md（BR-CHECKOUT-002）, glossary.md, README.md | いずれかの変更                                     |
| `02-question-analysis.md` | 01 と 12_quality/acceptance_criteria.md                                                                                                                                                                                                                 | 01 の変更、または 12_quality の変更                |
| `03` 〜 `05`              | 01 / 02 の結果                                                                                                                                                                                                                                          | 上流の変更、または保留の承認結果                   |
| 参考（判断に使わない）    | 12_quality/requirements_traceability.md                                                                                                                                                                                                                 | 変更があっても期待結果には影響しない（追跡性のみ） |

## ブロック中 / 保留

- 承認待ち: PA-01〜PA-16（`pending-approvals.md`）。すべて未承認。
- ブロック中の範囲: TR-014 全体、TR-008 の承認成功系、TCN-001-CI06、TCN-003-CI02、TCN-004-CI07/10/11、TCN-005-CI04/05、TCN-006-CI06（一部）、TCN-007-CI04/06、TCN-008-CI03/04、TCN-009-CI07、TCN-010-CI05/06。
- 継続可能な範囲: 上限の基本式、同一SKU合算の基本、0削除、統合の基本規則と abandoned、利用主体、状態遷移（規定の範囲）、表示時・チェックアウトの再検証の存在と問題の表示、二重送信の不変条件、画面状態の基本表示、Android 代表ケース。

## 残存リスク（要約。詳細は `03-test-analysis.md`）

- R-01 上限超過統合・カートバージョン・承認ゲート・二重実行の利用者向け挙動（保留）
- R-02 Android の空状態・問題明細（保留）
- R-03 iOS 自動検証（製品スコープによる対象外）
- R-04 並行操作（保留）
- R-05 具体値（上限・ランク）はテストデータ設計で確認

## 機械証拠（runtime-v2）の状態: 未実施

- 本ワークフローでは、`spec-analysis`・`test-analysis`・`test-requirement-design`・`test-condition-design` の runtime 実行（`runtime_contract.py` の `verify_runtime_evidence`、`requirement_structure`、`condition_structure` 等）を実行していない。
- そのため、本成果物の `Machine Runtime / Entity` 節は「未実施」と明記している。各 Skill の最終 runtime evidence gate を通していないため、これらの成果物は**契約上の完成扱いにしない**。人間可読の設計案としての利用に限る。
- 機械証拠が必要になった時点で、各 Skill の runtime を入力を組み立てて実行し直す（入力は本ファイルと上記 MD から作れる）。

## 次の一手（承認後）

1. プロダクトオーナーが `pending-approvals.md` の PA-01〜PA-16 を決定する（特に PA-01 カートバージョン、PA-02 上限超過統合、PA-04 価格変更承認、PA-10/05/06 統合の残余・主体・失敗系）。
2. 決定内容を `spec-analysis` で仕様根拠へ反映し、`change-process.md` の手続きで仕様書を改版する（本ワークフローでは改版しない）。
3. `question-analysis` で回答を正規化し、影響する `04` / `05` のみ再検証する。
4. 次工程 `test-case-design`（具体値・期待結果・手順）へ進むかは依頼に応じて判断。

## 自己検証の扱い

- 入力契約（対象機能・要求成果物・対象範囲）は満たしている。停止条件（仕様根拠の不足・競合）は、全体停止ではなく該当範囲のブロック中として処理した。
- 成果物はオーケストレーション契約（開始点、再利用記録、ブロック中の範囲化、修正ルーティング）に沿っている。
- 機械証拠（runtime-v2）が未実施のため、最終 runtime evidence gate を通した「契約適合済み・完成済み」とは扱わない。この制約はこのファイルと各成果物に明示した。
