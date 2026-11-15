# テスト観点・条件 / カバレッジ項目 出力

> **ステータス: 未完成（machine runtime evidence 未取得のためブロック中）。** この成果物は契約適合済み・完成済みとして扱わないでください。以下の判定は入力記述からの人手による導出であり、runtime 結果ではありません。

## 観点範囲

- 対象テスト要求: `TR-DATA-012`（テスト内容: current target A・Bのtest data requirementを適用対象別に合成し、conflictを対象別に報告すること）
- テストレベル: システムテスト
- 対象外: なし（入力に指定なし）
- 仮定 / 未解決事項:
  - `SPEC-DATA-012` は入力で「承認済み・current」と記載されるのみで、Authority本文と Machine Entity は入力に含まれない。本成果物は入力記載を根拠とする。
  - current model `M-ORDERS` の Machine Entity 内容（`model_key`、`model_type`、`technique_slug` 等）は入力に含まれない。
  - `version` の typed value 型は入力に明示がない。`version_range` の境界は入力どおり `2.0` / `1.4` の版文字列、`version = 1.3` は入力どおり exact version として扱う。
  - `TR-DATA-012` の優先度、関連プロダクトリスクは入力に含まれない。
  - 作成環境では runtime script（`test_data_requirements.py`、`runtime_contract.py`）を実行できなかった。

## テスト条件へ展開しないテスト要求

該当なし（`TR-DATA-012` は下記の観点・条件へ展開する）。

## 入力requirementの適用範囲（入力記述からの導出）

| requirement | dimension | operator / 値         | 適用対象                  | 根拠                                                 |
| ----------- | --------- | --------------------- | ------------------------- | ---------------------------------------------------- |
| R-ROLE      | role      | enum `{admin, guest}` | target A・B（model-wide） | 入力: model-wide requirement                         |
| R-A-LOW     | version   | `>= 2.0`（片側範囲）  | target A のみ             | 入力: target A の exact source target version を参照 |
| R-A-HIGH    | version   | `<= 1.4`（片側範囲）  | target A のみ             | 入力: target A の exact source target version を参照 |
| R-B-VERSION | version   | `= 1.3`（exact）      | target B のみ             | 入力: target B の exact source target version を参照 |

## テスト観点・条件一覧

| 観点ID     | テスト要求ID | テスト観点 / 条件                                                                                                                                     | カテゴリ          | テスト技法 / 根拠                                                                        | カバレッジ基準                                              | 関連仕様根拠 / プロダクトリスク | 優先度                                     | 備考                     |
| ---------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------- | ------------------------------------------ | ------------------------ |
| TCN-012-01 | TR-DATA-012  | target A の適用 requirement 集合（model-wide の `R-ROLE` と target A 参照の `R-A-LOW` / `R-A-HIGH`）を導出し、role・version の各 dimension で評価する | 正常系 / 合成     | Test Data Requirements / Materialization（model-wide 適用、同一 target 内 intersection） | target A × {role, version} の 2 セルを評価                  | SPEC-DATA-012（入力記載）       | 未指定（TR-DATA-012 の優先度が入力になし） |                          |
| TCN-012-02 | TR-DATA-012  | target B の適用 requirement 集合（`R-ROLE` と `R-B-VERSION`）を導出し、role・version の各 dimension で評価する                                        | 正常系 / 合成     | 同上                                                                                     | target B × {role, version} の 2 セルを評価                  | SPEC-DATA-012（入力記載）       | 未指定                                     |                          |
| TCN-012-03 | TR-DATA-012  | target A の version dimension で `R-A-LOW`（>= 2.0）と `R-A-HIGH`（<= 1.4）の intersection を評価し、conflict を target A に対して報告する            | 異常系 / 矛盾検出 | 同上（互換性のない要求を隠さない）                                                       | target A × version の 1 セルを評価                          | SPEC-DATA-012（入力記載）       | 未指定                                     | 両者の intersection は空 |
| TCN-012-04 | TR-DATA-012  | target-specific requirement を参照先 target 以外へ適用しない（R-A-* を B へ、R-B-VERSION を A へ適用しない。B に version conflict を報告しない）      | 境界 / 分離       | 同上（適用対象が異なる target 同士は cross-intersect しない）                            | 対象別の適用集合が参照 target と一致することを確認          | SPEC-DATA-012（入力記載）       | 未指定                                     |                          |
| TCN-012-05 | TR-DATA-012  | 全体 result は target A の conflict により unresolved とし、target B が互換であることで A の conflict を打ち消さない                                  | 異常系 / 集約     | 同上                                                                                     | conflict 件数と対象 target が全 target について一致すること | SPEC-DATA-012（入力記載）       | 未指定                                     |                          |

## カバレッジ項目一覧

| カバレッジ項目ID | 観点ID     | カバレッジ項目                                                                                                                                | 導出元の技法 / 基準                      | 期待挙動の根拠                        | 優先度 | 備考                            |
| ---------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------- | ------ | ------------------------------- |
| TCN-012-CI01     | TCN-012-01 | target A × role: `R-ROLE`（`{admin, guest}`）を適用し、他 requirement と非交差。intersection は非空（互換）                                   | Test Data Requirements / Materialization | 入力の `R-ROLE`、`SPEC-DATA-012`      | 未指定 | conflict を期待しない           |
| TCN-012-CI02     | TCN-012-03 | target A × version: `R-A-LOW ∩ R-A-HIGH` = 空 → target A の version conflict（requirement_keys: `R-A-HIGH`, `R-A-LOW`）を blocking として報告 | 同上                                     | 入力の範囲記述、`SPEC-DATA-012`       | 未指定 | 具体的な version 値は創作しない |
| TCN-012-CI03     | TCN-012-02 | target B × role: `R-ROLE` を適用し、互換                                                                                                      | 同上                                     | 入力の `R-ROLE`、`SPEC-DATA-012`      | 未指定 |                                 |
| TCN-012-CI04     | TCN-012-02 | target B × version: `R-B-VERSION`（`= 1.3`）のみで、conflict なし                                                                             | 同上                                     | 入力の `R-B-VERSION`、`SPEC-DATA-012` | 未指定 | 型は未確定（未解決事項参照）    |
| TCN-012-CI05     | TCN-012-04 | target 分離: target A の適用集合に `R-B-VERSION` を含めず、target B の適用集合に `R-A-LOW` / `R-A-HIGH` を含めない                            | 同上                                     | 入力の target version 参照            | 未指定 |                                 |

## カバレッジ候補の扱い

| 候補                                                     | 導出元                     | 扱い       | 理由 / 根拠                                                                                                              | カバー先                          |
| -------------------------------------------------------- | -------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------- |
| target A の version から具体的なテストデータ値を導出する | `R-A-LOW` / `R-A-HIGH`     | ブロック中 | target A の version 要求が互換性なく空集合のため、具体値を作ると要求を隠すことになる。上流で解消されるまで値を創作しない | TCN-012-CI02（conflict 報告のみ） |
| `R-B-VERSION` の target A への適用                       | 入力の target version 参照 | 対象外     | 入力で target B の exact source target version のみを参照                                                                | —                                 |
| `R-A-LOW` / `R-A-HIGH` の target B への適用              | 入力の target version 参照 | 対象外     | 入力で target A の exact source target version のみを参照                                                                | —                                 |

## Machine Runtime / Entity / Target mapping（機械証拠）

- runtime 実行: **未実行**（`artifact:test_data_requirements:all`）。作成環境で runtime script を実行できなかったため、runtime 結果・Machine Entity・`verify_runtime_evidence` の結果はこの成果物に含まれない。手組みの evidence は記載しない。
- 最終 runtime evidence gate: 未通過。
- Target mapping（入力記載値のみ。`target_ref` は runtime の target-ref rule で導出する必要があり、未実行のため記載しない）:

| target key | target_content_fingerprint（入力）                                      | generation_fingerprint（入力）                                          | target_ref | 人手の予備判定（runtime 結果ではない）   |
| ---------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------- | ---------- | ---------------------------------------- |
| A          | sha256:1111111111111111111111111111111111111111111111111111111111111111 | sha256:2222222222222222222222222222222222222222222222222222222222222222 | 未導出     | role 互換 / version conflict（blocking） |
| B          | sha256:3333333333333333333333333333333333333333333333333333333333333333 | sha256:4444444444444444444444444444444444444444444444444444444444444444 | 未導出     | role 互換 / version 互換                 |

## 未解決事項・契約上の制約

1. runtime 未実行のため、`test_data_requirements` の機械結果（`result_status`、`conflicts`、Entity）が未取得。完成扱いにできない。
2. target A の version 要求（`R-A-LOW: >= 2.0` と `R-A-HIGH: <= 1.4`）が空集合。仕様側で境界の正誤・優先関係を確定する必要がある（上流判断）。解消まで target A の具体的テストデータは作らない。
3. `SPEC-DATA-012` の Authority 本文・Machine Entity と、current model `M-ORDERS` の Machine Entity 内容が入力に含まれない。入力記載の「承認済み・current」を機械的に確認していない。
4. `version` の typed value 型（string / decimal 等）が未指定。版比較の型は上流で確定が必要。
5. `TR-DATA-012` の優先度と関連プロダクトリスクが未指定のため、観点・カバレッジ項目の優先度は未確定。

## 次の担当Skill

- 上記 2・4（version 矛盾、型）の解消 → `question-analysis`
- 解消後の runtime 再実行と `materialize_coverage`、その後の具体的テストケース設計 → `test-case-design`
