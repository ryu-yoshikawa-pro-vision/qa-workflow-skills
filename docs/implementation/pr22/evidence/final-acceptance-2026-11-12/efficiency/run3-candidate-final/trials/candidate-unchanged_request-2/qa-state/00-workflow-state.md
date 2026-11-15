# QAワークフロー状態: カート（Cart）

## 要求

- 対象: カート機能（`product/docs/spec/features/cart.md`）
- 実施範囲: テスト分析 → テスト要求 → テスト観点・条件（カバレッジ基準・項目）設計まで
- 除外: テストケース詳細化（`test-case-design`）、カバレッジ分析（`coverage-analysis`）、独立レビュー（`adversarial-review`）、テスト実行、製品コード・仕様書の変更
- 承認が必要な項目: `05-pending-and-questions.md` に保留として記録（先へ進めていない）
- シェル制約: `python3 <絶対path>` 形式のみ

## 入力revision

| 項目                         | 値                                                                                      | 確認状況（2026-11-13 再確認）                 |
| ---------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------------- |
| 製品commit                   | `2a8bcf57`（依頼者の指定）                                                              | `product/` に `.git` が無いため未検証（P-19） |
| `docs/spec/features/cart.md` | sha256 `385777e56a0d1c7ff52a187d9654a4343c74f88634c1f9b04411eaec897c7216`（5308 bytes） | **前回記録と一致（再利用）**                  |

関連入力の指紋（`product/` 直下相対path、`qa-state/tools/fingerprint_inputs.py` で計算）:

| 相対path                                     | sha256                                                             | bytes |
| -------------------------------------------- | ------------------------------------------------------------------ | ----- |
| `docs/spec/README.md`                        | `c63c81266b8c131a78d5a4048231e7c6dafceb433802bc18f0164903e220c854` | 5060  |
| `docs/spec/product-scope.md`                 | `23508ebe243d011e5e707039ffa6ddcb8d02612974877a58e1c3ced2cc789189` | 8455  |
| `docs/spec/roles-and-permissions.md`         | `519731749c55d9e01602017f9041d7ac9cc7e94e9ea0f86f16fd003dff12224e` | 3833  |
| `docs/spec/state-and-scenarios.md`           | `ccd0cab4b0bd156ea611c0bfad331b16f023d49acec4d95118d7fab70b8b4b90` | 4140  |
| `docs/spec/unresolved-specifications.md`     | `c3ac09d0f145d97380ee1cf0e59180a53dcf0806aff20a5af6dde4d72fe056aa` | 1076  |
| `docs/spec/known-deviations.md`              | `518d110c069d82bb20303dee57feb968633f98b9223c38d879a211e205c89edd` | 538   |
| `docs/spec/features/storefront.md`           | `3f77926ad16369ea5091672cf1c165ddf2f7f7f12f01512596d1e2a907c58c4a` | 12935 |
| `docs/spec/features/checkout-and-payment.md` | `9877302a255eb33e23a0651963930978543f4511a9457ca053e08df8ab859c76` | 13031 |
| `docs/spec/features/native-customer.md`      | `ed7f655ef5bc5f5bbb3928c063e484c90c94ac6f0f897f7e0a650970cc5152df` | 2721  |
| `docs/spec/screen-catalog.md`                | `8f30822b3adbfa839334119250051e5179c6a92c2cdba86e931f33afb21fdeb3` | 10237 |
| `docs/07_testability/seed_catalog.md`        | `5004ed590a29a7d9b2be84b8c0374996c1a6e2d4b26361773af4fa34a3fe8b76` | 19197 |

- 前回の記録は「指紋は計算済み」とだけ書かれ値が残っていなかったため、今回は値を記録した。今回の値を次回の比較基準とする。
- 比較は今回初めて値を保存したため、前回の値との一致は確認できていない。cart.md のみ前回値（`385777e5…7216`）と一致した。
- 参考（正本ではない）: `docs/reports/2026-08-01_ui-ux-user-journey-deep-exploration.md`。入力の正本には含めず、P-20 の参考情報としてのみ扱う。

| 項目                        | 値                                                                                                  | 確認状況                                         |
| --------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 案件Project Context（QA用） | 未発見。`product/docs/PROJECT_CONTEXT.md` は製品開発用の運用文書で、QA案件のProject Contextではない | `project-context` は未実行（P-17）               |
| 既存QA成果物                | `01`〜`05` の手作業草案（前回セッション作成）                                                       | 入力（cart.md）が同一のため再利用。runtime未検証 |

## 今回（2026-11-13）の実施記録

1. 既存state・成果物（`01`〜`05`）を読み、入力revisionを比較した。cart.md の指紋は一致したため、`01`（仕様Authority）、`03`（テスト要求）、`04`（テスト観点・条件）は**再利用**し、再生成していない。
2. 仕様の抜き取り確認（ROLE-CART、停止・退会の扱い、RANK、SCOPE-NATIVE、STATE-CART、STATE-REVALIDATE、SCREEN-BOUNDARY-FORBIDDEN、BR-CHECKOUT-002）を実施し、`01` の記載と一致することを確認した。
3. テスト可能性の補正: `02` と `05`（P-09）で、価格変更・在庫不足・非公開化は `cart-with-invalid-items` で初期状態として既に用意されることを反映した。実行中にそれらを起こす手段の不足は残している。ランク不足は gold / platinum 限定商品で作れることを追記した。
4. `05` に P-20（参考情報: 価格同意操作の報告、統合超過シナリオへの言及）と P-21（正本の指紋確認の状態）を追加した。いずれも期待結果の根拠には使わない。
5. runtime gate: 各Skillの `runtime_contract.py` / `workflow_runtime.py` は標準入力（stdin）からJSON envelopeを読む。依頼のシェル制約（`python3 <絶対path>` 形式のみ、パイプ・リダイレクト・`cd` 不可）では入力を渡せないため、**今回も実行していない**。`verify_runtime_evidence` の最終gateは未通過。
6. 今回の範囲外として未実行: `test-case-design`、`coverage-analysis`、`adversarial-review`。

## Skill実行状態

| Skill                     | 対象 / 実行範囲           | 状態                                                  | 成果物                        |
| ------------------------- | ------------------------- | ----------------------------------------------------- | ----------------------------- |
| `spec-analysis`           | カート（BR/AC/画面状態）  | 完了（手作業、runtimeなし）。今回抜き取り確認済み     | `01-spec-authority.md`        |
| `question-analysis`       | 仕様の曖昧さ・欠落の分類  | 完了（分類のみ、正式な回答収集は未実施）              | `05-pending-and-questions.md` |
| `test-analysis`           | `テスト分析`              | 完了（手作業、runtime未実行）。テストデータ記述を補正 | `02-test-analysis.md`         |
| `test-requirement-design` | テスト要求                | 完了（手作業、runtime未実行）                         | `03-test-requirements.md`     |
| `test-condition-design`   | `テスト設計` の条件・観点 | 完了（手作業、runtime未実行）                         | `04-test-conditions.md`       |
| `coverage-analysis`       | 範囲外                    | 未実行                                                | -                             |
| `adversarial-review`      | 範囲外                    | 未実行                                                | -                             |
| `test-case-design`        | 範囲外                    | 未実行                                                | -                             |

## 機械証拠（runtime）の扱い

- 各設計Skillの runtime / `verify_runtime_evidence` による機械証拠は **未生成**。上記の stdin 制約による。
- したがって `01`〜`04` は **手作業で作成した設計草案であり、runtime検証済みではない**。
- workflow stateは `qa.workflow_state_root` が未設定のため、helperによる永続化は行っていない。本Markdownを状態表として扱う。
- 補助スクリプト `qa-state/tools/fingerprint_inputs.py` は読み取りのみ。

## 完了判定

- 要求範囲（テスト分析〜テスト観点・条件設計）: 手作業の成果物は揃っている。ただし機械検証（runtime gate）が未通過のため「機械検証済み」とは判定しない。
- 未解決（ブロック中または保留）は `05-pending-and-questions.md` に一覧化した。ブロッカー（P-01〜P-05）が残るため、ワークフロー状態は**部分完了（ブロック中あり）**。
- ワークフロー全体（テストケース、カバレッジ分析、レビュー、実行、報告）は範囲外のため未完了。
- 最終runtime evidence gate未実施のため、本成果物は「契約適合済み・完成済み」とは扱わない。
