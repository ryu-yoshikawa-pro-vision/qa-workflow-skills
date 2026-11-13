# QAワークフロー状態: カート機能

- 対象製品: `product/`（commit 2a8bcf57）
- 対象仕様: `product/docs/spec/features/cart.md`（正式な製品動作 + BR/AC）
- 要求された範囲: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ項目）設計まで。詳細テストケース以降は対象外
- 進行モード: `continuous`（既定。案件コンテキストでのgated指定はなし）
- 製品コード・仕様書: 変更していない
- 最終更新: 2026-11-13

## 改版履歴

- 2026-11-13: 外部仕様書改版（`product-change-spec.diff`）。BR-CART-001の上限値 99 → 50。AC-CART-001は未変更で「99」が残存（矛盾、Q-011）。影響の詳細は`change-impact-product-change-spec.md`。

## 工程状態

| 工程（Skill）                          | 対象 / 実行範囲 | 状態                                     | 成果物                          | 備考                                                                   |
| -------------------------------------- | --------------- | ---------------------------------------- | ------------------------------- | ---------------------------------------------------------------------- |
| spec-analysis                          | —               | 完了（下書き・改版反映）                 | `01-spec-analysis.md`           | SPEC-002を50へ更新。SPEC-007を要確認（UNK-011）                        |
| question-analysis                      | —               | 完了（下書き・改版反映）                 | `02-question-analysis.md`       | 局所ブロッカー6件（Q-011追加）、要確認5件                              |
| test-analysis                          | テスト分析      | 完了（下書き・要再検証あり）             | `03-test-analysis.md`           | RISK-001を要再検証（上限変更、実装乖離）。採点は未再実施               |
| test-requirement-design                | —               | 部分完了（ブロック中あり・要再検証あり） | `04-test-requirement-design.md` | TR-001を50へ更新、要再検証。ブロック中 TR-014, 016, 017, 018           |
| test-condition-design                  | —               | 部分完了（ブロック中あり）               | `05-test-condition-design.md`   | TCN-001・CI07〜09・TCN-014-CI02を50へ更新。TCN-001-CI10（Q-011）を追加 |
| test-case-design                       | —               | 対象外（今回の範囲外）                   | —                               |                                                                        |
| coverage-analysis / adversarial-review | —               | 対象外（今回の範囲外）                   | —                               |                                                                        |

## 完了判定

- ワークフロー全体の状態: **部分完了（ブロック中あり・要再検証あり）**
- 理由: 要求範囲の工程は改版を反映済みだが、ブロック中（Q-001, Q-002, Q-007, Q-008, Q-009, Q-011）が残り、RISK-001 / TR-001が要再検証のまま（test-analysisの再採点、P-013の回答後）。完了ではない。
- 局所ブロックの影響範囲: TR-002の追加0、TR-006の判定値（規則は継続）、TR-014、TR-016、TR-017、TR-018、TR-019のiOS部分、TR-001のAC由来99部分（TCN-001-CI10）。それ以外のTRと TCNは継続可能。

## 実装との乖離（要判断）

- 仕様（BR-CART-001）は上限50。実装定数は `product/src/domain/services/cart.ts` の `CART_QUANTITY_LIMIT = 99`、`product/src/application/contracts/common.ts` の `maxCartQuantity: 99`。
- 実装を50へ合わせるか、仕様を戻すかはプロダクト責任者の判断（P-013）。QA側では仕様（50）を期待結果の根拠とし、実装は変更していない。

## 機械証拠（runtime）の状態

- 各Skillの `scripts/runtime_contract.py` / `workflow_runtime.py` / `verify_runtime_evidence` は **未実行**（初版と同じ）。
- 理由: 厳密なJSON入力（Entity・fingerprint・依存関係）の生成を本作業で検証できていない。改版反映は既存成果物の直接更新で行った。
- 影響: 各成果物は人手による下書きであり、qa-workflowの最終runtime evidence gateを通っていない。よって**契約適合済み・完成済みとは扱わない**。

## 保留（承認待ち）

`pending-approvals.md` を参照（決定・回答が必要な項目 13件、仮定候補 3件）。今回追加: P-012（AC-CART-001の99）、P-013（実装定数と仕様の乖離）。

## 再開方法

1. `pending-approvals.md`の項目に回答を得る（特に P-012 AC-CART-001の文言、P-013 実装との整合方針、P-001 版、P-008 合計金額）。
2. 回答を`spec-analysis`で正式な仕様根拠（SPEC / DEC / ASM）へ正規化し、`01-spec-analysis.md`を更新する。
3. 影響する下流だけを再開する: 99境界（TCN-001-CI10、P-012）、版（TR-016）、合計金額（TR-014）、補助文書の挙動（TR-017）、統合境界（TR-018）、数量入力（TR-002）。
4. P-013の回答後に`test-analysis`でRISK-001を再採点し、必要なら`test-requirement-design`以降を見直す。
5. 機械証拠の生成は、必要なら別途実施する。

## 上流変更時の伝播（今回の改版）

- 変更した最も早い成果物: SRC-001（cart.md）→ SPEC-002。
- 影響を受けた下流: SPEC-007（矛盾）、Q-011（新規）、RISK-001（要再検証）、TR-001（要再検証）、TCN-001・CI07〜09（更新）、TCN-001-CI10（新規・ブロック中）、TCN-014-CI02（更新）。
- 影響なし: TR-002〜013、TR-015〜019、TCN-002〜013、TCN-015〜020（上限値に依存しない）。
