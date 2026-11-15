# テスト観点・条件 / カバレッジ項目

## 観点範囲

- 対象テスト要求: TR-ORDERS-014（注文一覧の表示対象〔model `M-ORDERS`のcurrent target A／B／C〕を、正式なCoverage Itemで漏れなく確認する）
- テストレベル: システムテスト（入力のTR assignment）
- 対象外: なし（入力に対象外指定はない）
- 仮定 / 未解決事項:
  - TR-ORDERS-014の優先度・プロダクトリスクは入力に含まれないため未確定。優先度は推測で設定していない。
  - 根拠: SPEC-ORD-014（承認済み・current）。入力の文言「`重複`のDispositionは、cover先targetのcurrent execution mappingで閉じられる場合に限り確認済みとする」をカバレッジ基準として使用。
  - model `M-ORDERS`はcurrent Machine Entityとして確認済み（入力記載）。
  - 本成果物はcondition_structure runtimeを実行していない（後述「Machine Runtime / Entity / Target mapping」を参照）。

## テスト条件へ展開しないテスト要求

| テスト要求ID | 扱い | 理由 / 根拠                                                                                                    |
| ------------ | ---- | -------------------------------------------------------------------------------------------------------------- |
| （なし）     | —    | TR-ORDERS-014は本成果物でTCN-014へ展開する。別テストレベル・残存リスク・対象外・ブロック中への振り分けはない。 |

## item × 共通condition候補の正式適用（formal_design入力時）

formal_design入力はないため、本節は対象外。

## テスト観点・条件一覧

| 観点ID  | テスト要求ID  | テスト観点 / 条件                                                                               | カテゴリ                | テスト技法 / 根拠                                                                                                    | カバレッジ基準                                                                                                                                                         | 関連仕様根拠 / プロダクトリスク         | 優先度                                      | 備考                             |
| ------- | ------------- | ----------------------------------------------------------------------------------------------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------- | -------------------------------- |
| TCN-014 | TR-ORDERS-014 | 注文一覧の表示対象（model `M-ORDERS`のcurrent target全件）が、Coverage Itemで確認されていること | 画面表示 / 表示対象網羅 | 専用の技法は適用しない。モデル既存のcurrent target集合の網羅であり、coverage-techniques.mdに対応する技法規則はない。 | M-ORDERSのすべてのcurrent target（A／B／C）をCoverage Itemで確認する。`重複`のtargetは、cover先targetのcurrent execution mappingで閉じられる場合に限り確認済みとする。 | SPEC-ORD-014 / プロダクトリスク: 未提供 | 未確定（TR-ORDERS-014の優先度が入力になし） | 充足状況は下記「充足状況」を参照 |

## カバレッジ項目一覧

| カバレッジ項目ID | 観点ID  | カバレッジ項目                                                                                                                      | 導出元の技法 / 基準              | 期待挙動の根拠 | 優先度 | 備考                                                                                                                                            |
| ---------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | -------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| TCN-014-CI01     | TCN-014 | target B（current version: `target_content_fingerprint=sha256:bbbb…bbbb`、`generation_fingerprint=sha256:dddd…dddd`）の表示対象確認 | target集合の網羅（SPEC-ORD-014） | SPEC-ORD-014   | 未確定 | current execution mapping `CI-001` へ接続済み。`CI-001`の`execution_fingerprint`はBのcurrent mappingと一致（入力記載）。                        |
| TCN-014-CI02     | TCN-014 | target C（current version: `target_content_fingerprint=sha256:eeee…eeee`、`generation_fingerprint=sha256:ffff…ffff`）の表示対象確認 | target集合の網羅（SPEC-ORD-014） | SPEC-ORD-014   | 未確定 | 現時点でCIへ未到達（入力記載）。未閉鎖のため、model completionは未達成。execution mappingは本成果物では作成しない（test-case-design側の担当）。 |

## カバレッジ候補の扱い

| 候補                                                                                                                  | 導出元                   | 扱い | 理由 / 根拠                                                                                                                                                                                                                                                                                | カバー先                         |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------- |
| target A（current version: `target_content_fingerprint=sha256:aaaa…aaaa`、`generation_fingerprint=sha256:cccc…cccc`） | M-ORDERSのcurrent target | 重複 | 意味上Bと重複。Dispositionの`covered_by_target_version`はBのcurrent version（`bbbb…bbbb`／`dddd…dddd`）を参照。AからBへのself reference / cycleはない。BはCI-001へcurrent mappingされ、CI-001の`execution_fingerprint`がBのcurrent mappingと一致するため、SPEC-ORD-014の重複条件を満たす。 | target B → TCN-014-CI01 → CI-001 |

採用候補（B・C）は上記「カバレッジ項目一覧」へ位置づけ、「重複」には含めない。

## 充足状況（model completion）

- 候補母集団: model `M-ORDERS`のcurrent target 3件（A、B、C）
- 閉じた件数: 2件
  - A: 重複としてB経由で閉鎖（上記）
  - B: TCN-014-CI01 → CI-001で接続済み
- 未閉鎖: 1件
  - C: TCN-014-CI02はCIへ未接続
- coverage status: 2/3 closed（incomplete）。100%とはしない。
- model completion: 未達成。target Cのexecution mappingが確定するまでTR-ORDERS-014のカバレッジは完了しない。

## 任意: デシジョンテーブル / 状態遷移表 / Pairwise・組合せ

該当なし（入力に条件の組合せ・状態遷移の規則はない）。

## 統合候補

| 候補     | 統合理由                                            | カバー先                 |
| -------- | --------------------------------------------------- | ------------------------ |
| target A | 意味上Bと重複。SPEC-ORD-014の重複規則で閉じられる。 | target B（TCN-014-CI01） |

## Machine Runtime / Entity / Target mapping（機械証拠）

本成果物では`condition_structure`を含む決定論的runtimeを実行していない。

- 理由: 入力（eval-input.md）はTR-ORDERS-014、M-ORDERSのtarget、Disposition、CI-001 mapping、SPEC-ORD-014を文章とfingerprintで記述しているのみで、runtimeが要求するcanonical Machine Entity envelope（TR entity、model entity、disposition、mapping entity）と`test_conditions`／`models`のcanonical drafts、metadataが含まれない。推測で補完すると機械証拠を創作することになるため行わない。
- 加えて、このセッションではshell実行（Bash）の権限が拒否され、scriptを起動できなかった。
- そのため `render_runtime_input()` / `render_runtime_result()` / `render_machine_entities()` の結果、`materialize_coverage`の結果、`verify_runtime_evidence` の判定は存在しない。

target mapping（人間向け記述、機械証拠ではない）:

| target | target_content_fingerprint | generation_fingerprint | 状態                                          | CI                     |
| ------ | -------------------------- | ---------------------- | --------------------------------------------- | ---------------------- |
| A      | sha256:aaaa…aaaa           | sha256:cccc…cccc       | 重複（covered_by_target_version = B current） | —（B経由）             |
| B      | sha256:bbbb…bbbb           | sha256:dddd…dddd       | current mapping済み                           | CI-001（TCN-014-CI01） |
| C      | sha256:eeee…eeee           | sha256:ffff…ffff       | CI未到達                                      | 未割当（TCN-014-CI02） |

## 現在残っている契約上の制約

- Machine runtime evidence（condition_structure結果、materialize結果、最終runtime evidence gate）が未取得のため、本成果物は契約適合済み・完成済みとして扱わない。
- target C（TCN-014-CI02）のexecution mappingが未確定のため、model completionは未達成。
- TR-ORDERS-014の優先度・プロダクトリスクが未確定。
- 次の担当: target Cの実行手順・CI mappingの作成は`test-case-design`へ委ねる。
