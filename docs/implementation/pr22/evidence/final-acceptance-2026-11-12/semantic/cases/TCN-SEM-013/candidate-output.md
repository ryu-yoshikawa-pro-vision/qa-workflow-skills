# テスト観点・条件 / カバレッジ項目 出力（ブロック中）

## 観点範囲

- 対象テスト要求: 未特定（テスト要求ID・仕様根拠が入力に含まれない）
- テストレベル: 未特定
- 対象外: なし（判断材料なし）
- 仮定 / 未解決事項:
  - 同一TCN（ID未指定）の current target A・B、別modelの target C について、execution fingerprint、expected result root、source target version の具体値が入力に含まれない。
  - target A・B の test data requirement（`role=admin` / `role=guest`）の dimension 定義、merge後CIへの union / intersection 規則の正本参照が入力に含まれない。
  - 条件設計の対象は materialization の grouping predicate と requirement 統合規則であり、製品behaviorの技法選択ではないという前提のみが与えられている。

## テスト条件へ展開しないテスト要求

| テスト要求ID | 扱い       | 理由 / 根拠                                                                                  |
| ------------ | ---------- | -------------------------------------------------------------------------------------------- |
| 未特定       | ブロック中 | テスト要求の意味を条件へ展開できる具体的な記述、および現在有効な仕様根拠が入力に存在しない。 |

## テスト観点・条件一覧

該当なし（ブロック中のため条件を生成しない）。

## カバレッジ項目一覧

該当なし（ブロック中のため項目を生成しない）。

## カバレッジ候補の扱い

| 候補                                                                                                       | 導出元   | 扱い       | 理由 / 根拠                                                                                                                                                     | カバー先 |
| ---------------------------------------------------------------------------------------------------------- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| grouping predicate（同一TCN・同一model・同一execution fingerprint・同一expected result root での統合判定） | 評価入力 | ブロック中 | 統合判定の入力値（fingerprint、expected result root、source target version、model所属）の具体値と判定規則の正本が入力にないため、採否・充足基準を定義できない。 | なし     |
| requirement union / intersection（`role` dimension の `admin` / `guest` 統合）                             | 評価入力 | ブロック中 | dimension定義、union / intersection の適用規則、merge後CIの正本参照が入力にないため、カバレッジ基準を定義できない。                                             | なし     |

## 機械証拠の状態

- materialize_coverage.py の入力（`models[]` の current model runtime 結果、`target_annotations`、`target_dispositions`、`test_data_requirements`、`merge_groups`、previous 系マップ、`inactive_*`、`zero_scope_terminal`）が入力に存在しないため、materialization を実行していない。
- 実行確認: 空の入力で `materialize_coverage.py` を実行したところ `invalid_input`（必須field不足）で `result_status: blocked` を返した。これは入力不足による拒否であり、本件の判定結果ではない。
- runtime結果・fingerprint・target IDを手組みで補完していない。current / deterministic / complete の状態は主張しない。

## 停止理由（既存停止条件への該当）

- 現在有効な仕様根拠を解決できない。
- テスト要求の意味が曖昧で条件へ展開できない。
- カバレッジ基準を定義するために不可欠な仕様（merge規則、dimension定義）がない。

## 必要な追加入力

1. 対象TCNのID、テスト要求ID、現在有効な仕様根拠（merge規則の正本を含む）。
2. target A・B・C それぞれの stable target ID、target version、execution fingerprint、expected result root、model所属。
3. A・B の test data requirement（dimension定義と `role` 値）および merge_groups 定義。
4. 上記から current model runtime 結果を生成するための upstream runtime 出力（手組み不可）。

以上の入力が揃うまで、本件は完成扱いにしません。
