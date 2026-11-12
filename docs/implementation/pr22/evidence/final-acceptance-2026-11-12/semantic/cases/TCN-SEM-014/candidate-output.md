# テスト観点・条件 / カバレッジ項目 出力

## 観点範囲

- 対象テスト要求: TR-ORDERS-014（注文一覧の表示対象 target A／B／C を正式なCoverage Itemで漏れなく確認する）
- テストレベル: 未確認（入力に記載なし）
- 対象外: なし（入力で対象外と判断された候補はない）
- 仮定 / 未解決事項:
  - 現在有効な仕様根拠（target A／B／Cの表示対象ごとの期待挙動の出典）が入力に提示されていない。
  - 正規化済みの機械入力（canonical normalized input）と、current model runtimeのMachine Runtime Result envelopeが提示されていない。
  - target A／B／Cの内容（何を表示し、どの値・条件で何が変わるか）が入力に記載されていない。

## 全体判定

- TR-ORDERS-014: ブロック中
- モデル `M-ORDERS` の完了判定: 完了不可（complete化しない）
- coverage status: unknown（機械的な materialize_coverage 結果が無いため算出不能）

## テスト条件へ展開しないテスト要求

| テスト要求ID  | 扱い       | 理由 / 根拠                                                                                                                                                                                                                                 |
| ------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TR-ORDERS-014 | ブロック中 | 現在有効な仕様根拠が解決できず、target B／Cの期待挙動を未承認推論で補わないと条件（テスト観点・カバレッジ項目）を作れないため。停止条件「現在有効な仕様根拠を解決できない」「期待挙動を未承認推論で補完しないと条件を作れない」に該当する。 |

## テスト観点・条件一覧

該当なし。TR-ORDERS-014 はブロック中のため、テスト観点・条件（TCN）は作成しない。

## カバレッジ項目一覧

該当なし。期待挙動の仕様根拠が無いため、カバレッジ項目（TCN-xxx-CIxx）は採番しない。

## target の扱い（モデル M-ORDERS）

| target | current version（入力に記載の値）                                                                                      | 扱い                 | 理由 / 根拠                                                                                                                                                            | カバー先                                                                                                                                                      |
| ------ | ---------------------------------------------------------------------------------------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A      | target_content_fingerprint=sha256:aaaa…（64桁、入力記載どおり）／generation_fingerprint=sha256:cccc…（入力記載どおり） | 重複（入力上の判断） | 入力は「意味上Bと重複」と記載。ただし同じ検証責務である根拠（A/Bの表示対象の内容比較）は提示されていない。                                                             | target B（current version: target_content_fingerprint=sha256:bbbb…、generation_fingerprint=sha256:dddd…）。A→B の self reference / cycle は無い（入力記載）。 |
| B      | target_content_fingerprint=sha256:bbbb…／generation_fingerprint=sha256:dddd…                                           | ブロック中           | CI-001 へ current mapping 済み（入力記載の execution_fingerprint は B の current mapping と一致）。ただし B の期待挙動の仕様根拠が無く、Coverage Item を定義できない。 | 未確定（CI-001 は B の current mapping として入力に記載）                                                                                                     |
| C      | target_content_fingerprint=sha256:eeee…／generation_fingerprint=sha256:ffff…                                           | ブロック中           | current version は存在するが CI へ未到達。期待挙動の仕様根拠も無く、Coverage Item を定義できない。                                                                     | 未確定（CI 未到達）                                                                                                                                           |

- fingerprint は入力の記載値をそのまま転記したものであり、runtime による照合（currentness・stale 判定）は未実施。
- A の「重複」は、B が完了するまで検証責務の充足として扱わない。B が未完了の間は A も検証済みとしない。

## カバレッジ候補の扱い

| 候補     | 導出元                     | 扱い       | 理由 / 根拠                                                                      | カバー先 |
| -------- | -------------------------- | ---------- | -------------------------------------------------------------------------------- | -------- |
| target A | M-ORDERS の current target | 重複       | 入力の判断（意味上 B と重複）。根拠の提示は限定的。                              | target B |
| target B | M-ORDERS の current target | ブロック中 | 仕様根拠・期待挙動が不足。CI-001 への mapping は存在するが、内容の充足は未確認。 | —        |
| target C | M-ORDERS の current target | ブロック中 | 仕様根拠・期待挙動が不足。CI 未到達。                                            | —        |

## Machine Runtime / Entity / Target mapping（機械証拠）

- 入力に current model runtime の Machine Runtime Result envelope、canonical normalized input は提示されていないため、`runtime_contract.py::current_model_result_row()` および `materialize_coverage.py` の実行は行わなかった（推測で入力を組み立てない方針）。
- `verify_runtime_evidence` も、正規化済み入力が無いため実行していない。
- 上記のため、stable target ID・Machine Entity・freshness の機械的な照合結果は本成果物に存在しない。
- 必要な機械証拠（target A／B／C の current runtime result、CI-001 の current mapping の runtime 結果）が揃うまで、本モデルの target mapping を complete として扱わない。

## 解消に必要な上流確認事項

1. TR-ORDERS-014 の現在有効な仕様根拠（target A／B／C の表示対象ごとの期待挙動の出典）
2. target A と B の重複判断の根拠（表示対象の内容比較）
3. target C の期待挙動と、CI への到達（Coverage Item の割当先）
4. target B の期待挙動と、CI-001 の内容が B の表示対象を網羅していること
5. canonical normalized input と current model runtime の結果（fingerprint の currentness 照合に必要）

上記が解消された後に、テスト観点・条件とカバレッジ項目を再設計する。
