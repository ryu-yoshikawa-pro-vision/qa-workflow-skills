# テスト観点・条件 / カバレッジ項目（TR-MERGE-013）

**状態: 未完成。runtime evidence未取得のため、機械証拠付きの完成扱いにできません。** 下記の条件は承認済み仕様 `SPEC-MAT-013` と `coverage-techniques.md`「Test Data Requirements / Materialization」から導出した人間向け記述で、runtime結果ではありません。

## 観点範囲

- 対象テスト要求: `TR-MERGE-013`（テストレベル: システムテスト）
- 根拠仕様: `SPEC-MAT-013`（承認済み・current）。merge許可条件と同一dimension requirementのintersection / conflict拒否を定める。
- テスト対象の性質: 製品behaviorの技法選択ではなく、materializationのgrouping predicateとtest data requirement合成の決定性を検証する。
- 対象外: 入力に対象外の指定なし。
- 仮定 / 未解決事項:
  - 既存のTCN IDが入力に記載されていないため、本書のCI IDは `TCN-XXX-CI##` の仮ラベルとする（実IDへの割当は未確定）。
  - 入力の「current modelのMachine Entityは確認済み」について、Entity本体・target ID・execution fingerprint・expected result root の実値は入力に含まれない。
  - TR-MERGE-013の優先度、プロダクトリスクは入力に記載なし。
  - runtime（`materialize_coverage`、`test_data_requirements`、`verify_runtime_evidence`）は未実行（後述）。

## テスト条件へ展開しないテスト要求

該当なし。`TR-MERGE-013`はテスト条件へ展開する。

## item × 共通condition候補の正式適用（formal_design入力時）

該当なし（formal_design入力なし）。

## テスト観点・条件一覧

| 観点ID     | テスト要求ID | テスト観点 / 条件                                                                                                                                                     | カテゴリ                      | テスト技法 / 根拠                                  | カバレッジ基準                                                                           | 関連仕様根拠 / プロダクトリスク                               | 優先度                           | 備考                                                                               |
| ---------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------- | ---------------------------------------------------------------------------------- |
| TCN-XXX-C1 | TR-MERGE-013 | 対象A・Bが同一TCN・同一model・current target version・同一execution fingerprint・同一expected result rootを全て満たすとき、grouping候補になる                         | 正常系（merge許可条件の充足） | materialization規則（predicate全項目の充足を判定） | 全4キー一致のA・Bを1組の候補として判定する                                               | SPEC-MAT-013 / 優先度未指定                                   | 未指定（TR優先度を継承・要確認） | requirement合成の結果（C5）と合わせて最終判定                                      |
| TCN-XXX-C2 | TR-MERGE-013 | 対象Cは同一execution fingerprintと同一expected result rootを持つが別modelに属するため、A・Bとgroupingしない                                                           | 境界（model不一致）           | materialization規則（predicate項目ごとの不一致）   | Cを含む統合が生成されないことを確認する                                                  | SPEC-MAT-013 / 優先度未指定                                   | 未指定                           | 入力で指定された唯一のmodel差分ケース                                              |
| TCN-XXX-C3 | TR-MERGE-013 | predicateの各項目（同一TCN、同一model、current target version、同一execution fingerprint、同一expected result root）のいずれか1つが不一致なら、grouping候補にならない | 境界（項目ごとの不一致）      | materialization規則（「すべて一致する場合だけ」）  | 5項目それぞれについて1項目のみ不一致の組を個別に確認する                                 | SPEC-MAT-013 / 優先度未指定                                   | 未指定                           | stale target（source target versionが非current）は現行として受理せずgroupingしない |
| TCN-XXX-C4 | TR-MERGE-013 | 同一dimensionのrequirementが衝突する（A: `role=admin`、B: `role=guest`、intersection = ∅）場合、mergeを拒否し統合CIを作らない                                         | 異常系（conflict拒否）        | materialization規則（同一dimension intersection）  | A・Bの統合CIが生成されないこと、およびconflictが注記のみで有効扱いされないことを確認する | SPEC-MAT-013 / 優先度未指定                                   | 未指定                           | **確認待ち**（下記「ブロック中の論点」参照）                                       |
| TCN-XXX-C5 | TR-MERGE-013 | 同一dimensionのrequirementが衝突しない（intersectionが非空）場合、grouping候補の統合が許可される                                                                      | 正常系（intersection非空）    | materialization規則（同一dimension intersection）  | 同一値などintersectionが非空の組でmergeが許可されることを確認する                        | SPEC-MAT-013（conflict拒否の対偶として導出）/ 優先度未指定    | 未指定                           | 入力に具体的なintersection非空ケースは無いため、導出条件として扱う                 |
| TCN-XXX-C6 | TR-MERGE-013 | 異なるdimensionのrequirementは同一dimension intersectionの対象外となり、同時成立するrequirement unionとして扱われる                                                   | 境界（dimension差）           | materialization規則（requirement union）           | union結果を確認する                                                                      | **仕様根拠不足**（SPEC-MAT-013の抜粋に異dimensionの扱いなし） | 未指定                           | 仕様根拠が解決されるまでブロック中                                                 |
| TCN-XXX-C7 | TR-MERGE-013 | 同じ入力（候補の列挙順を変えた場合を含む）に対し、grouping結果・requirement合成結果・CI IDが毎回同一になる                                                            | 決定性                        | materialization規則（deterministic grouping）      | 同一入力の複数回実行・入力順変更で出力が一致することを確認する                           | TR-MERGE-013（「決定的に働くこと」） / 優先度未指定           | 未指定                           | runtime結果が取得できるまで確認不可                                                |

## カバレッジ項目一覧

| カバレッジ項目ID | 観点ID     | カバレッジ項目                               | 導出元の技法 / 基準 | 期待挙動の根拠             | 優先度 | 備考                           |
| ---------------- | ---------- | -------------------------------------------- | ------------------- | -------------------------- | ------ | ------------------------------ |
| TCN-XXX-CI01     | TCN-XXX-C1 | A・Bの全4キー一致による候補判定              | materialization規則 | SPEC-MAT-013               | 未指定 | 仮ID                           |
| TCN-XXX-CI02     | TCN-XXX-C2 | Cとの非grouping（model差分）                 | materialization規則 | SPEC-MAT-013               | 未指定 | 仮ID                           |
| TCN-XXX-CI03     | TCN-XXX-C3 | predicate項目1つ不一致の5ケース              | materialization規則 | SPEC-MAT-013               | 未指定 | 5件へ具体化する（キー別）      |
| TCN-XXX-CI04     | TCN-XXX-C4 | role衝突（admin ∩ guest = ∅）によるmerge拒否 | materialization規則 | SPEC-MAT-013               | 未指定 | 期待結果の前提確認待ち         |
| TCN-XXX-CI05     | TCN-XXX-C5 | intersection非空による統合許可               | materialization規則 | SPEC-MAT-013の対偶（導出） | 未指定 | 具体値は未確定                 |
| TCN-XXX-CI06     | TCN-XXX-C6 | 異dimensionのrequirement union               | materialization規則 | **根拠不足**               | 未指定 | ブロック中                     |
| TCN-XXX-CI07     | TCN-XXX-C7 | 同一入力での決定的出力                       | materialization規則 | TR-MERGE-013               | 未指定 | 実行回数・入力順の指定は未確定 |

## カバレッジ候補の扱い

| 候補                                                        | 導出元                                | 扱い                       | 理由 / 根拠                                                                                                                                                               | カバー先 |
| ----------------------------------------------------------- | ------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| A・B統合が成立する前提（「両方がmerge後のCIへ適用される」） | 入力の前提記述                        | ブロック中                 | 同一dimensionの`role=admin`と`role=guest`はintersectionが∅でconflictとなり、SPEC-MAT-013に従えばmergeは拒否される。入力の前提と規則が矛盾するため、期待挙動を確定できない | —        |
| 異dimension requirementのunion                              | 入力の「union/intersection contract」 | ブロック中                 | SPEC-MAT-013の抜粋に異dimensionの合成規則がなく、仕様根拠不足                                                                                                             | —        |
| 不明operatorを含むrequirementの扱い                         | coverage-techniques規則               | 対象外（今回の入力範囲外） | 入力のTR-MERGE-013はeq/同一dimension衝突に限定されている。採否は要確認                                                                                                    | —        |

## 任意: デシジョンテーブル

grouping predicateは4項目の連言として表せるため、条件列挙の補助として使用する（runtime非実行）。

| ルール | 同一TCN             | 同一model | current target version | 同一execution fingerprint | 同一expected result root | requirement intersection | 結果       | 対応観点ID     | 対応カバレッジ項目ID     |
| ------ | ------------------- | --------- | ---------------------- | ------------------------- | ------------------------ | ------------------------ | ---------- | -------------- | ------------------------ |
| 1      | ○                   | ○         | ○                      | ○                         | ○                        | 非空                     | 統合許可   | TCN-XXX-C1, C5 | TCN-XXX-CI01, CI05       |
| 2      | ○                   | ×         | ○                      | ○                         | ○                        | —                        | 統合しない | TCN-XXX-C2     | TCN-XXX-CI02             |
| 3      | ○                   | ○         | ○                      | ○                         | ○                        | ∅（conflict）            | 統合拒否   | TCN-XXX-C4     | TCN-XXX-CI04（確認待ち） |
| 4〜8   | 各項目1つ×（他は○） | —         | —                      | —                         | —                        | —                        | 統合しない | TCN-XXX-C3     | TCN-XXX-CI03             |

## 任意: 状態遷移表

該当なし。

## 任意: Pairwise / 組合せ

該当なし（組合せ生成は実施していない）。

## 統合候補

| 候補                                                    | 統合理由         | カバー先                       |
| ------------------------------------------------------- | ---------------- | ------------------------------ |
| C3の5ケースは同一の判定規則（全項目一致の連言）に属する | 判定の責務は同じ | TCN-XXX-CI03内でキー別に具体化 |

## Machine Runtime / Entity / Target mapping（機械証拠）

**未取得。** 次の理由で、runtime結果・Machine Entity・target mappingを生成していません。

- Bash実行権限が拒否されたため、`materialize_coverage.py` / `test_data_requirements.py` / `runtime_contract.py`（`verify_runtime_evidence`）を実行できなかった。
- 両runtimeは `metadata`（upstream entities、runtime_unit_key、static_data_versions 等）と `input` を含む正規化JSONを要求する。入力にはtarget ID、execution fingerprint、expected result root、Machine Entityの実値がないため、これらを推測で作成することはしない。

## 完成に必要な残件

1. **Bash実行権限の付与後、`materialize_coverage`（A・B・Cを含むcanonical入力）と`test_data_requirements`を実行し、結果を本節へ配置する。** これが得られ、`verify_runtime_evidence`が`valid=true`を返すまで完成扱いにしない。
2. **ブロック中の論点（人間の確認が必要）:** 入力の「両方がmerge後のCIへ適用される」は、`role=admin`と`role=guest`の同一dimension衝突と両立しない。SPEC-MAT-013に従い「mergeを拒否する」とするか、衝突しない別requirementの前提だったかを確認する。確認までTCN-XXX-CI04の期待結果は確定しない。
3. **仕様根拠不足:** 異dimension requirementの合成（TCN-XXX-CI06）について、SPEC-MAT-013または関連仕様の該当箇所を確認する。
4. TR-MERGE-013の優先度、既存TCN IDを確認し、仮ラベル（TCN-XXX）を実IDへ置き換える。
