# 00. ワークフロー状態 — カート機能

- 対象製品: `product/`（commit 2a8bcf57。`product/`にgitメタデータがなく、commit一致は未検証）
- 対象機能: カート（`product/docs/spec/features/cart.md`）
- 依頼の範囲: テスト分析からテスト観点（条件）設計まで
- 進行モード: `continuous`（既定）。承認が必要な項目は`90_pending_approvals.md`で保留し、先へ進めた
- 制約: 製品コード・仕様書は変更しない。シェルは`python3 <絶対path>`の形でのみ使用（今回は未使用）

## 工程の状態

| 工程             | Skill                     | 対象 / 実行範囲 | 成果物                    | 状態                 | 備考                                                                                            |
| ---------------- | ------------------------- | --------------- | ------------------------- | -------------------- | ----------------------------------------------------------------------------------------------- |
| 仕様分析         | `spec-analysis`           | —               | `01_spec_analysis.md`     | 完了（前回）・再確認 | `cart.md`とFR-CA-001〜018を突合し、整合を確認。ただし情報源の権威判定に差し戻し事項あり（下記） |
| 不明点分析       | `question-analysis`       | —               | `02_question_analysis.md` | 完了（前回）・再確認 | Q-001〜Q-012。権威判定の結果に応じて再分類が必要な可能性あり                                    |
| テスト分析       | `test-analysis`           | `テスト分析`    | `03_test_analysis.md`     | 完了（今回）         | RISK-001〜013。runtime未実行の手作業                                                            |
| テスト要求       | `test-requirement-design` | —               | `04_test_requirement.md`  | 完了（今回）         | TR-001〜024。根拠の層を明記                                                                     |
| テスト観点・条件 | `test-condition-design`   | —               | `05_test_condition.md`    | 完了（今回）         | TCN-001〜032、カバレッジ項目（CI）。runtime未実行の手作業                                       |
| テストケース     | `test-case-design`        | —               | —                         | 対象外（依頼範囲外） | —                                                                                               |
| カバレッジ分析   | `coverage-analysis`       | —               | —                         | 対象外（依頼範囲外） | —                                                                                               |
| 反証レビュー     | `adversarial-review`      | —               | —                         | 対象外（依頼範囲外） | —                                                                                               |
| 生きた対象確認   | `test-target-inspection`  | —               | —                         | 未実施               | 版数・active cart・ゲストカート状態の観測手段が未確認                                           |

## ブロック中 / 保留

| 範囲                                                                                                      | 理由                       | 解消条件                                                         |
| --------------------------------------------------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------- |
| TR-006, TCN-009                                                                                           | Q-002                      | 在庫減少の扱いの回答                                             |
| TR-008（guest）, TCN-013                                                                                  | Q-001                      | ゲストの価格変更承認の回答                                       |
| TR-009（前提状態）, TCN-016                                                                               | Q-007                      | 統合の前提状態の回答                                             |
| TR-012（版数競合）, TCN-021                                                                               | Q-004                      | 古い版数の扱いの回答                                             |
| TR-018, TCN-027                                                                                           | Q-005                      | 合計金額の算出規則の回答（候補の算出式はあるが正式根拠ではない） |
| TR-024                                                                                                    | Q-008                      | Androidの要否の回答                                              |
| TR-020（保持期限）                                                                                        | Q-009                      | 保持期限の回答（対象外候補）                                     |
| TR-002, TCN-007 / TR-012（二重実行）, TCN-020 / TR-017（追加時価格）, TCN-026-CI02 / TR-016（操作の種類） | Q-003, Q-006, Q-010, Q-012 | 期待結果の回答（条件は設計済み）                                 |

## 要権威判定（P-001）

`docs/spec/README.md`の「正式な製品動作」の正本一覧は、`product-scope.md`・`roles-and-permissions.md`・`state-and-scenarios.md`・`ui-ux-contract.md`・`features/**/*.md`に限られる。01の多くのSPEC（FR-CA、acceptance_criteria、`03_domain/business_rules.md`を根拠とするもの）は、この一覧の外にある。今回の分析では、`04`の「根拠の層」列で正式（cart.md / authentication.md）と要権威判定を区別した。

## 差し戻し（上流）

- `spec-analysis`の情報源に`product/docs/03_domain/business_rules.md`（カートの規則、価格計算、送料無料の閾値5,000円、版数、統合の通知、表示順）が含まれていない。取り込みの要否は権威判定（P-001）に依存する。
- 01の「要件の正本」としての扱い（SRC-002 / SRC-003）は、`docs/spec/README.md`の正本判定と一致していない可能性がある。spec-analysisで再判定が必要。
- 上記の結果により、01・02の一部が`要再検証`になる可能性がある。現時点では`要再検証`へは戻していない（権威判定の結論が出るまで保留）。

## 機械証拠

今回、`analysis_entities` / `risk_matrix` / `requirement_structure` / `condition_structure`等のruntimeは一切実行していない。Machine Runtime Input / Result / Entityは未付与。各成果物の末尾に、その旨を記載した。

## 再開手順

1. `90_pending_approvals.md`のP-001（権威判定）とQ-001〜Q-012の回答を受け取る。
2. P-001の結論に従い、`spec-analysis`を再実行して情報源と権威を更新する（`01`の更新）。
3. `question-analysis`で回答を正規化し、ブロック中範囲を更新する（`02`の更新）。
4. 影響するTRとTCNだけを`要再検証`として再設計する（`04` / `05`）。
5. 次の工程（`test-case-design`、`coverage-analysis`、`adversarial-review`）は、依頼があった場合に進める。
