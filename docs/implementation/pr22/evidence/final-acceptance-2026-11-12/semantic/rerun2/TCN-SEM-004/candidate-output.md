# テスト観点・条件 / カバレッジ項目: SPEC-CRUD-001（order-lifecycle）

> **状態: 未完成（runtime未実行）**。下記の定義は入力のCRUD matrixとAuthority記述から読み取った内容です。`crud_matrix`など機械runtimeの結果とverify証拠は付いていません。機械証拠は手組みしていません。runtime結果が得られるまで、この成果物は契約適合済み・完成済みとは扱えません。

## 観点範囲

- 対象テスト要求: 入力にテスト要求IDがないため未付与。要求は「SPEC-CRUD-001のCRUD matrix・sequence・postconditionに基づくCRUD Coverage Itemを作る」こととして扱う。
- テストレベル: 未提示（テスト要求またはTR Entityがないため解決できない）。
- 対象外: 入力に対象外の指定はない。
- 仮定 / 未解決事項:
  - SPEC-CRUD-001は入力記述を現在有効な仕様根拠として扱う。現在有効性の照合は行っていない。
  - 業務操作（place / get / amend / cancel / reserve / adjust / release / charge / adjust / refund）は、matrixでの配置をCRUD operationへの対応として採用する。業務操作から別のCRUD operationを推測しない。
  - 個別業務操作の期待結果はSPEC-CRUD-001に定義がない。定義されているのはsequenceのpostconditionだけである。
  - 優先度・プロダクトリスクは未提示のため、優先度は未設定とする。

## テスト条件へ展開しないテスト要求

該当なし。唯一の要求をテスト条件へ展開した。

## テスト観点・条件一覧

テスト技法: CRUD Testing（completenessとconsistencyを別々に閉じる）。

| 観点ID  | テスト要求ID | テスト観点 / 条件                                                                        | カテゴリ          | テスト技法 / 根拠             | カバレッジ基準                                       | 関連仕様根拠 / プロダクトリスク | 優先度 | 備考                                 |
| ------- | ------------ | ---------------------------------------------------------------------------------------- | ----------------- | ----------------------------- | ---------------------------------------------------- | ------------------------------- | ------ | ------------------------------------ |
| TCN-001 | 未付与       | Order × order-lifecycle のC／R／U セルの各業務操作が定義どおり存在し、検証対象になる     | CRUD completeness | CRUD / SPEC-CRUD-001 matrix   | 当該セルに配置された業務操作を全件カバー             | SPEC-CRUD-001                   | 未設定 | D は not_applicable（扱い表参照）    |
| TCN-002 | 未付与       | InventoryReservation × order-lifecycle のC／U／D セルの各業務操作を検証対象にする        | CRUD completeness | CRUD / SPEC-CRUD-001 matrix   | 当該セルに配置された業務操作を全件カバー             | SPEC-CRUD-001                   | 未設定 | R は not_applicable（扱い表参照）    |
| TCN-003 | 未付与       | BillingBalance × order-lifecycle のR／U セルの各業務操作を検証対象にする                 | CRUD completeness | CRUD / SPEC-CRUD-001 matrix   | 当該セルに配置された業務操作を全件カバー             | SPEC-CRUD-001                   | 未設定 | C・D は not_applicable（扱い表参照） |
| TCN-004 | 未付与       | Order のlifecycle sequence `place → amend → cancel` を実行し、その後の状態関係を確認する | CRUD consistency  | CRUD / SPEC-CRUD-001 sequence | 指定sequenceを1件実行し、postcondition 3件を全て確認 | SPEC-CRUD-001                   | 未設定 | 後述の制約を参照                     |

## カバレッジ項目一覧

| カバレッジ項目ID | 観点ID  | カバレッジ項目（CRUD cell / 業務操作 / postcondition）                                   | 導出元の技法 / 基準 | 期待挙動の根拠                                                              | 優先度 | 備考                                                                 |
| ---------------- | ------- | ---------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------------------------------------- | ------ | -------------------------------------------------------------------- |
| TCN-001-CI01     | TCN-001 | Order / order-lifecycle / C（place）                                                     | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 期待結果の詳細は未定義（確認事項1）                                  |
| TCN-001-CI02     | TCN-001 | Order / order-lifecycle / R（get）                                                       | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-001-CI03     | TCN-001 | Order / order-lifecycle / U（amend）                                                     | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-001-CI04     | TCN-001 | Order / order-lifecycle / U（cancel）                                                    | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義。cancelled状態はTCN-004-CI02で扱う   | 未設定 | 同上                                                                 |
| TCN-002-CI01     | TCN-002 | InventoryReservation / order-lifecycle / C（reserve）                                    | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-002-CI02     | TCN-002 | InventoryReservation / order-lifecycle / U（adjust）                                     | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-002-CI03     | TCN-002 | InventoryReservation / order-lifecycle / D（release）                                    | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義。全量release済みはTCN-004-CI03で扱う | 未設定 | 同上                                                                 |
| TCN-003-CI01     | TCN-003 | BillingBalance / order-lifecycle / R（get）                                              | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上。TCN-004-CI04の観測にも使う想定                                 |
| TCN-003-CI02     | TCN-003 | BillingBalance / order-lifecycle / U（charge）                                           | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-003-CI03     | TCN-003 | BillingBalance / order-lifecycle / U（adjust）                                           | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-003-CI04     | TCN-003 | BillingBalance / order-lifecycle / U（refund）                                           | CRUD completeness   | セルの存在のみ。個別の期待結果は未定義                                      | 未設定 | 同上                                                                 |
| TCN-004-CI01     | TCN-004 | sequence `order-place-amend-cancel` を place（C）→ amend（U）→ cancel（U）の順に実行する | CRUD consistency    | SPEC-CRUD-001のsequence定義                                                 | 未設定 | 実行の成立は期待結果ではなくsequence定義に基づく                     |
| TCN-004-CI02     | TCN-004 | postcondition: Order が cancelled である                                                 | CRUD consistency    | SPEC-CRUD-001 postcondition                                                 | 未設定 | Authority定義あり                                                    |
| TCN-004-CI03     | TCN-004 | postcondition: InventoryReservation が全量release済みである                              | CRUD consistency    | SPEC-CRUD-001 postcondition                                                 | 未設定 | Authority定義あり。単一entityのruntime sequenceでは表せない（制約2） |
| TCN-004-CI04     | TCN-004 | postcondition: BillingBalance が place 前の残高へ戻る                                    | CRUD consistency    | SPEC-CRUD-001 postcondition                                                 | 未設定 | Authority定義あり。place前残高の取得方法は確認事項3。制約2           |

## カバレッジ候補の扱い

| 候補                                                        | 導出元                     | 扱い                                              | 理由 / 根拠                                                                                            | カバー先 |
| ----------------------------------------------------------- | -------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | -------- |
| Order × D（delete）                                         | CRUD matrix completeness   | not_applicable（Authority: SPEC-CRUD-001 matrix） | SPEC-CRUD-001 matrixがOrder deleteをnot_applicableと定義                                               | —        |
| InventoryReservation × R（read）                            | CRUD matrix completeness   | not_applicable（Authority: SPEC-CRUD-001 matrix） | SPEC-CRUD-001 matrixがInventoryReservation readをnot_applicableと定義                                  | —        |
| BillingBalance × C（create）                                | CRUD matrix completeness   | not_applicable（Authority: SPEC-CRUD-001 matrix） | SPEC-CRUD-001 matrixがBillingBalance createをnot_applicableと定義                                      | —        |
| BillingBalance × D（delete）                                | CRUD matrix completeness   | not_applicable（Authority: SPEC-CRUD-001 matrix） | SPEC-CRUD-001 matrixがBillingBalance deleteをnot_applicableと定義                                      | —        |
| InventoryReservation / BillingBalance の lifecycle sequence | CRUD consistency（未提示） | 未採用（作成しない）                              | SPEC-CRUD-001はsequenceを1件（order-place-amend-cancel）しか定義しない。順序を創作しないため採用しない | —        |

- 残存リスク・成立不能・重複・ブロック中の候補はなし。
- InventoryReservation / BillingBalance の状態変更操作（reserve / adjust / release、charge / adjust / refund）は、上記sequenceに含まれないが、completeness項目（TCN-002, TCN-003）として既にカバー対象。

## カバレッジ基準の集計（定義上）

- completeness（CRUD cell単位）: entity × operation の枠は3 × 4 = 12。定義済みcell 8（Order: C／R／U、InventoryReservation: C／U／D、BillingBalance: R／U）と not_applicable 4 で、12枠すべてが閉じている。業務操作単位では11件（TCN-001〜003の各CI）を定義した。
- consistency: Authorityが定義するsequence 1件（required 1）を採用し、postcondition 3件（TCN-004-CI02〜CI04）を項目化した。
- 実行結果・期待結果の確定はtest-case-designへ委ねる。個別業務操作の期待結果は未定義のため、確定していない。

## 確認事項・制約

1. 個別業務操作（place / get / amend / cancel / reserve / adjust / release / charge / adjust / refund）の期待結果がSPEC-CRUD-001に定義されていない。TCN-001〜003の項目は「セルが存在し検証対象になる」ことまでを定義している。期待結果の詳細は`question-analysis`で確定するまで未確定とする。
2. TCN-004のpostconditionは、Order・InventoryReservation・BillingBalance にまたがる。単一entityのsequenceを表すruntime modelでは、この横断的な状態関係をそのまま機械的に表せない。そのため、この関係は本成果物の記述だけで保持している。
3. BillingBalanceの「place前の残高」は相対的な値である。place前の残高をどの時点で、どの操作（候補: BillingBalance get、TCN-003-CI01）で観測するかはSPEC-CRUD-001に定義がなく、確認が必要である。
4. InventoryReservation と BillingBalance には、Authorityで定義されたlifecycle sequenceがない。その状態変更操作は、completeness項目としてのみカバーしている。これらの順序付きsequenceが必要かどうかは、上流の判断を要する。
5. テスト要求ID、テストレベル、優先度（リスク）が入力にない。TCN-001〜004の関連テスト要求は未付与、優先度は未設定である。

## Machine Runtime / Entity mapping（機械証拠）

- 未添付。`crud_matrix`（model:crud-001）、親`condition_structure`、`verify_runtime_evidence`のいずれも実行していない。実行環境でBashの実行権限が拒否されたため。
- 実行用の入力は `cases/TCN-SEM-004/runtime/crud-request.json` に保存している（`crud_matrix.py`へstdinとして渡す想定）。
- runtime-v2 / entity-state-v2の証拠は手組みしていない。runtime結果が得られるまで、target_ref、CI ID、execution fingerprintの対応は確定していない。
