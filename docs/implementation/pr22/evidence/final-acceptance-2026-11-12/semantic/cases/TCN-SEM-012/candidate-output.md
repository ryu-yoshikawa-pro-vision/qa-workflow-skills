# テスト観点・条件 / カバレッジ項目 出力

## 観点範囲

- 対象テスト要求: 未提供（入力はテスト要求ではなく、source model `M-ORDERS` のテストデータ要求のみ）
- テストレベル: 未解決
- 対象外: なし
- 仮定 / 未解決事項: 下記「ブロック中」を参照

## 結論

テスト条件・カバレッジ項目は生成しません。状態は**ブロック中**です。

## ブロック理由（停止条件該当）

1. テスト要求が未提供: 入力は「何を検証するか」を示していません。テスト要求を条件へ展開できません（基本停止条件1）。
2. 現在有効な仕様根拠が未提供: `R-ROLE`、`R-A-LOW`、`R-A-HIGH`、`R-B-VERSION`の`authority_refs`がありません。仕様根拠を解決できません（基本停止条件2）。
3. runtime入力が不足: `test_data_requirements` runtimeには、current model `M-ORDERS`のMachine Entity（content付き）、upstream runtime units、input_mode、requirementごとのdimension_key（version要件のdimension名を含む）、正規化済みtyped valueが必要です。入力はこれらを提供していません。現在の`M-ORDERS`を作るcondition_structure runtimeの結果もないため、runtimeは実行していません。推測でModel Entityやfingerprintを作ることはしません。
4. target_refの導出: 入力は`target_ref`を「runtime target-ref rule」で導出するとしていますが、current target A／Bの`target_ref`値そのものは提供されていません。target_refは`sha256(model_key, target_key)`で導出される規則ですが、導出結果を確定値として使うにはcurrent runtime結果が必要です。

## 参考: 入力テキストからの非runtime所見（確定結果ではない）

以下は入力文面の読み取りであり、runtime検証済みの結果ではありません。上記ブロックの解消後にruntimeで再確認が必要です。

| 要件                          | 種別                  | 適用対象（所見） | 備考                                |
| ----------------------------- | --------------------- | ---------------- | ----------------------------------- |
| R-ROLE: role ∈ {admin, guest} | enum, model-wide      | A, B             | 同一model内の全current targetへ適用 |
| R-A-LOW: version >= 2.0       | version_range（片側） | A のみ           | source target version A を参照      |
| R-A-HIGH: version <= 1.4      | version_range（片側） | A のみ           | source target version A を参照      |
| R-B-VERSION: version = 1.3    | eq                    | B のみ           | source target version B を参照      |

- 所見の衝突: target A の `version` 次元で `R-A-LOW`（>= 2.0）と `R-A-HIGH`（<= 1.4）が同時成立しません。影響はtarget Aのみです。
- target B には衝突所見はありません（`R-ROLE`と`R-B-VERSION`は同時成立可能）。
- 所見の前提: `version`を同一dimension_keyとみなすこと、`R-ROLE`の値が両targetで同一であることは入力文面からの読み取りです。dimension_keyは入力に明示されていません。

## テスト条件・カバレッジ項目

- 未生成（ブロック中のため）

## カバレッジ候補の扱い

- 未生成（テスト要求未提供のため）

## Machine Runtime / Entity / Target mapping（機械証拠）

- 未実行。`test_data_requirements`および`condition_structure`のruntime結果が存在しないため、機械証拠として配置できるものはありません。

## 未解消の契約上の制約

- 本成果物は契約適合済み・完成済みとして扱いません。テスト要求、仕様根拠、current model Machine Entity、target_ref導出結果が提供された後に再実行が必要です。
