# QA進行状態: カート機能（テスト分析 〜 テスト観点・条件設計）

- 対象製品: `product/`（commit 2a8bcf57）
- 主仕様: `product/docs/spec/features/cart.md`
- 実施範囲: テスト分析からテスト観点（条件）設計まで。テストケース設計、テスト実行、E2E、カバレッジ分析（最終）、独立レビューは対象外
- 更新日: 2026-11-13
- 進行モード: `continuous`（既定。案件コンテキストの指定なし）
- 製品コード・仕様書: 変更していない

## 工程状態

| 順   | 工程（担当Skill）                               | 成果物                    | 状態                                                                    |
| ---- | ----------------------------------------------- | ------------------------- | ----------------------------------------------------------------------- |
| 1    | 仕様分析（`spec-analysis`）                     | `01-spec-analysis.md`     | 完了（ただし非正式文書の扱いはQ-013の回答待ち）                         |
| 2    | 不明点・矛盾分析（`question-analysis`）         | `02-question-analysis.md` | 完了。ブロッカー2件（局所）、要確認11件、提案1件                        |
| 3    | テスト分析（`test-analysis`）                   | `03-test-analysis.md`     | 完了（リスク評価・技法選択）                                            |
| 4    | テスト要求設計（`test-requirement-design`）     | `04-test-requirements.md` | 完了。ブロック中の要求は無し。UNK依存の一部条件は次工程で局所ブロック中 |
| 5    | テスト観点・条件設計（`test-condition-design`） | `05-test-conditions.md`   | 完了。ブロック中の条件候補あり（局所）                                  |
| 保留 | 承認・回答待ち                                  | `pending-approvals.md`    | 保留中。仮定（ASM）は承認されるまで期待結果の根拠に使用しない           |

以降（テストケース設計、カバレッジ分析、独立レビュー）は本依頼の範囲外のため未実施です。

## 実施上の制約（重要）

- 本環境のシェルは `python3 <絶対path>` の形式のみ使用可能という指定だったため、各Skillの決定論的runtime（`runtime_contract.py` / `authority_entities.py` 等）は実行していません。これらは標準入力のJSONを受け取る方式で、指定形式では入力を渡せません。
- そのため、以下は**未生成**です。
  - Machine Runtime Input / Result / Machine Entity（各成果物の機械証拠ブロック）
  - 最終runtime evidence gate（`verify_runtime_evidence`）の結果
- したがって、各成果物は人間向けの分析・設計内容として作成しましたが、Skillの「runtime evidence gate通過」を要する完成判定は満たしていません。この扱いは`pending-approvals.md`の P-15 で判断をお願いします（標準入力を使える実行手段の許可、または機械証拠なしでの人間レビュー継続）。

## 次の一手

1. `pending-approvals.md` の保留事項（特に Q-001 / Q-002 の2件はブロッカー（局所））を仕様責任者へ確認する。
2. 回答を受けた後、`question-analysis` の再開先（`spec-analysis` / `test-condition-design`）へ影響範囲だけ戻す。
3. 機械証拠の扱い（P-05）が決まってから、runtime evidence gate を含めた最終確認を行う。
4. 承認後、テストケース設計（`test-case-design`）へ進む。

## ファイル一覧

- `01-spec-analysis.md` — 現在有効な仕様根拠（SPEC / DECISION / INFERENCE / UNKNOWN）
- `02-question-analysis.md` — 不明点の分類（ブロッカー / 要確認 / 仮定可能 / 提案）と再開先
- `03-test-analysis.md` — プロダクトリスク、設計深度、テスト技法、テストレベル
- `04-test-requirements.md` — テスト要求（TR）と上流項目の閉鎖
- `05-test-conditions.md` — テスト条件（TCN）、カバレッジ項目（CI）、候補の扱い
- `pending-approvals.md` — 保留（承認・回答待ち）の一覧

## 追補（2026-11-13）

- 既存の成果物を、非正式の要件書 `product/docs/01_requirements/functional_requirements.md`（FR-CA / FR-AU）と `product/docs/05_ui/screen_list.md` のカート記述に照らして再確認した。
- 追加した補助情報源: SUP-005（FR-CA / FR-AU）、SUP-006（screen_list 行97）。いずれも正式仕様（`spec/README.md` の正式一覧）ではないため、期待結果の根拠にはしていない。
- 新規の要確認: Q-015（数量超過時の理由表示の要否、非ブロッカー、P-16）。
- 既存のブロッカー（Q-001 / Q-002）とブロック中の条件は変更なし。補強候補として記録のみ。
- 既存成果物（01〜05）の工程状態は変えていない。
