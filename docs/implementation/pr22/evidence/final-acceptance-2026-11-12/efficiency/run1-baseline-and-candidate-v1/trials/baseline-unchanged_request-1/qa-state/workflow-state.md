# QAワークフロー状態: カート機能

- 対象製品: `product/`（commit 2a8bcf57）
- 対象仕様: `product/docs/spec/features/cart.md`（正式な製品動作 + BR/AC）
- 要求された範囲: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ項目）設計まで。詳細テストケース以降は対象外
- 進行モード: `continuous`（既定。案件コンテキストでのgated指定はなし）
- 製品コード・仕様書: 変更していない
- 最終更新: 2026-11-13（2回目: 補助文書との突合により Q-011 / P-012 を追加、TR-006 の文言を修正、TCN-007-CI08 を要確認として追加）

## 工程状態

| 工程（Skill）                          | 対象 / 実行範囲 | 状態                       | 成果物                          | 備考                                          |
| -------------------------------------- | --------------- | -------------------------- | ------------------------------- | --------------------------------------------- |
| spec-analysis                          | —               | 完了（下書き）             | `01-spec-analysis.md`           | 直接の正本（cart.md等）を解決。機械証拠なし   |
| question-analysis                      | —               | 完了（下書き）             | `02-question-analysis.md`       | 局所ブロッカー5件、要確認5件                  |
| test-analysis                          | テスト分析      | 完了（下書き）             | `03-test-analysis.md`           | 高リスク5件、中4件（RISK-001〜009）           |
| test-requirement-design                | —               | 部分完了（ブロック中あり） | `04-test-requirement-design.md` | TR-001〜019。ブロック中 TR-014, 016, 017, 018 |
| test-condition-design                  | —               | 部分完了（ブロック中あり） | `05-test-condition-design.md`   | TCN-001〜020。ブロック中の項目を含む          |
| test-case-design                       | —               | 対象外（今回の範囲外）     | —                               |                                               |
| coverage-analysis / adversarial-review | —               | 対象外（今回の範囲外）     | —                               |                                               |

## 完了判定

- ワークフロー全体の状態: **部分完了（ブロック中あり）**
- 理由: 要求範囲の工程は実施済みだが、ブロック中（Q-001, Q-002, Q-007, Q-008, Q-009）が残り、対象スコープに未解決のブロック中が残るため完了ではない。
- 局所ブロックの影響範囲: TR-002の追加0、TR-006の判定値（規則は継続）、TR-014、TR-016、TR-017、TR-018、TR-019のiOS部分。それ以外のTRと TCNは継続可能。

## 機械証拠（runtime）の状態

- 各Skillの `scripts/runtime_contract.py` / `workflow_runtime.py` / `verify_runtime_evidence` は **未実行**。
- 理由: これらは厳密なJSON入力（Entity・fingerprint・依存関係）を要求し、本作業でその正確な生成を検証できなかったため。`test-analysis/scripts/runtime_contract.py` を stdin 無しで実行すると「strict JSON decode失敗」を返すことのみ確認した。
- 影響: 各成果物は人手による下書きであり、qa-workflowの最終runtime evidence gateを通っていない。よって**契約適合済み・完成済みとは扱わない**。
- 次の対応: 機械証拠を生成するには、各Skillのruntime入力契約に従ってcanonical JSONを作成し、`verify_runtime_evidence`を通す必要がある。これは作業時間とtoken量の判断を要するため、継続可否を確認したい。

## 保留（承認待ち）

`pending-approvals.md` を参照（決定・回答が必要な項目 12件（P-001〜P-012）、仮定候補 3件）。今回追加:

- P-012 / Q-011: 価格変更以外の問題明細を承認で解除できるか。AC-CART-003（承認を4種に並置）と BR-CART-003・補助文書 business_rules §3（価格変更に限定）が衝突。修正・削除による解除は両読みで成立するため TR-006 は継続。承認による解除はTCN-007-CI08（要確認）のみ。

## 再開方法

1. `pending-approvals.md`の項目に回答を得る（特に P-001 版、P-008 合計金額、P-007 補助文書の正本化）。
2. 回答を`spec-analysis`で正式な仕様根拠（SPEC / DEC / ASM）へ正規化し、`01-spec-analysis.md`を更新する。
3. 影響する下流だけを再開する: 版（TR-016）、合計金額（TR-014）、補助文書の挙動（TR-017）、統合境界（TR-018）、数量入力（TR-002）。
4. 機械証拠の生成は、必要なら別途実施する。

## 上流変更時の伝播（今回の初版）

今回は初版のため、既存の有効成果物はない。今後、SPEC（cart.md）が変わった場合は、影響するSPEC項目を辿って TR → TCN の順に`要再検証`とする。
