# Test Reporting guidance

## 責務境界

| 事項                                      | 正本owner                                                                                                                                                                                                                      | 本Skill                                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| 計画版・対象source・build・終了基準・承認 | `test-management`（承認済み計画版）                                                                                                                                                                                            | 参照して計画上の母集団とする。更新しない  |
| 各方式の元結果・attempt・cleanup          | 各source owner（`test-execution` / `e2e-test-execution` / `testware-execution` / `exploratory-testing` / `regression-testing`のActivity / 静的レビュー・解析のowner / `usability-inspection` / `wcag-conformance-evaluation`） | 読取専用で集約。raw値を変換・再判定しない |
| 欠陥候補・外部Issue                       | `defect-management` / 外部Issueサービス                                                                                                                                                                                        | refのprojectionだけ。状態を更新しない     |
| Playwright E2E単体の人間向け報告          | `e2e-test-reporting`                                                                                                                                                                                                           | 置き換えない。E2Eは元結果として参照する   |
| QA活動の評価・改善                        | `test-evaluation`                                                                                                                                                                                                              | 報告snapshotを渡すだけ                    |
| リリース可否・リスク受容                  | 権限者                                                                                                                                                                                                                         | 判断しない                                |

## 1. 母集団（計画上の対象）

1. 計画の`planned_sources[]`から、source id・owner・方式（`kind`）・集計単位（`unit`）・期待する単位ref（`expected_refs`）または件数（`expected_count`）・build・環境を取得する。対象には一般TC、Playwright E2E、Regression、探索、API / バッチ / コンポーネント、非機能測定、静的レビュー・解析、UI/UX・WCAG、欠陥のうち計画が要求するものを含める。
2. 計画がない直接依頼では、明示されたscopeと許可されたdiscovery rootだけから母集団を作る。母集団が未知なら全体率と終了判定を`undetermined`にし、すべて発見済みと主張しない。
3. 期待する単位も件数も不明なsourceは`expected_population_unknown`で未完了にする。計画上対象がない（`no_target_confirmed`）ことが確認された空集合だけを0件の完了として扱う。

## 2. 取得（read-only）

1. 各sourceについて、取得状態、pagination完了、権限、source revision、取得時点、result ref、元結果のレコードを記録する。
2. 予定されたsourceが取得されていなければ0件とせず`取得未完了`とし、取得済みの部分集計と不足数・範囲を同時に出す。
3. 別build・別環境・source revisionが異なるレコード、および計画（またはsource）の対象期間`period`の外にあるレコードは集計から除外し、除外理由（`build_mismatch` / `environment_mismatch` / `record_source_revision_mismatch` / `period_mismatch`）を残す。対象期間が宣言されているのにレコードの`executed_at`がない・解釈できない場合は期間を確認できないため`period_unverified`として除外する。期間の定義が不正な計画は`plan_period_invalid`で確定しない。計画外の単位refは分母に加えず別記する。
4. 同じ`result_ref`で内容が同一の重複は1件にまとめる。同じ`result_ref`で内容が異なる場合、および同じ単位refに複数の結果がある場合は衝突として、どれも採用せず（入力順に依存させない）未完了にする。同じ`source_id`の取得結果が複数渡された場合も、どちらも採用せず曖昧な取得として未完了にし、再取得を求める。retryは`attempt`単位の別sourceとして取得し、`logical primary` / `resolved TestCase`の分母へ加算しない。非E2Eではテストファイル・suite・個別テスト・TC・testware refを別単位とし、ファイルの成功から個別テストの実行を推定しない。

## 3. 集計と閉鎖判定

`scripts/reporting_runtime.py build-snapshot`で決定論的に集計する。各sourceの完了は次の4つの独立した閉鎖から導出する。

- `population_complete`：計画対象の全単位が取得され、重複・衝突・件数差がなく、paginationと権限が完全。
- `source_current`：取得したsource revisionが現在のrevisionと一致。
- `results_observable`：すべての元結果が確定済み。状態は方式ごとの値域（実行系はPASS / FAIL / 未実行 / SKIP / 判定不能 / blocked、静的はreviewed / not_reviewed / tool_failed）に限る。
- `cleanup_closed`：実行方式のcleanupが成功・対象なし・意図的に残した状態。

未完了のsourceにはPASS率を出さず、取得分だけの参考値（`retrieved_only_pass_rate`）と明記する。単位別（`by_unit`）の率は、その単位のすべてのsourceが完了している場合だけ出す。異なる単位をまたぐ全体の件数・PASS率は出さない。静的レビューは、計画対象すべてのレビュー完了と完全取得がなければ「指摘0件・完了」を主張しない。

## 4. 終了基準

- 各基準は**単一の計測単位**かつ適用可能な方式のsourceだけを`source_ids`に持つ。`logical_primary`と`attempt`、正式TC（`resolved_testcase`）と個別テスト、補助testware、実行結果と静的レビューなど、単位や方式が異なるsourceを合算した率・件数で判定せず、その基準は`unknown`（`mixed_units_or_kinds_not_summable` / `metric_not_applicable_to_source_kind`）とする。同じ単位のsource（例：APIとコンポーネントの個別テスト）は基準が明示した場合に合算できる。
- 実行済み（`executed_rate`）はPASS・FAIL・判定不能の件数で、SKIP・未実行・blockedは含めない。

- 終了判定は、計画が承認済みで現在のrevisionであり、すべての終了基準が満たされ、母集団が完全な場合だけ`satisfied`。
- 母集団が不完全な率の基準は`unknown`。失敗件数の上限を観測済みの失敗がすでに超えている場合だけ、不完全でも`unsatisfied`にできる。
- 計画が未承認・失効・改版済みなら`undetermined`。旧計画revisionの報告をcurrentにしない。
- 現在の計画revision（`current_plan_revision`）が取得できていない場合は、改版済み（`superseded`）とは別に**未確認（`unverified`）**とし、終了判定を`satisfied`にしない（`plan_currentness`で`current` / `superseded` / `unverified`を区別）。
- リリース可否は`release_decision=not_determined_by_this_skill`で固定する。

## 5. 鮮度

snapshotは`snapshot_ref`（snapshot本体の全内容、すなわち件数・完全性・判定・取得したレコードのdigestを含むcontent hashから決定論的に生成）で識別する。同じ内容は常に同じref、内容が1つでも違えば別のrefになるため、immutableなcreate-if-absent保存でも別内容のsnapshotが同一視されない。`check-currentness`で計画revisionと各sourceの現在revisionを比較し、変化していれば`stale`、現在revisionを取得できなければ`unverified`とする（いずれも`current`ではない）。履歴snapshotを再計算して書き換えない。欠陥Issueの更新も新しいsource revisionとして再報告する。

## 6. 停止条件

- 計画・source・権限の不足は該当sourceだけを未完了にし、取得済みの範囲は報告する。
- secret・cookie・token・storageState・個人情報を報告へ転載しない。
- 保存が必要な場合、新規はcreate-if-absent、更新はexpected revisionのCAS、保存後readbackを必要とし、能力がなければ保存をblockedにする。
