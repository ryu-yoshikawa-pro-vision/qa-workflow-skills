# Test Reporting data contract

## 入力

- `plan`：`plan_ref`、`plan_revision`、`approval_state`（`approved` / `draft` / `expired` / `revoked`）、`scope_ref`、`build_ref`、`environment_ref`、`period{from, to}`（対象期間。ISO 8601、`from <= to`）、`planned_sources[]`、`exit_criteria[]`。
  - `planned_sources[]`：`source_id`、`owner_skill`、`kind`（`general_tc` / `e2e` / `regression` / `exploration` / `api` / `batch` / `component` / `nonfunctional` / `uiux` / `wcag` / `static_review` / `static_analysis` / `defect`）、`unit`、`expected_refs[]`または`expected_count`、`no_target_confirmed`、任意で`build_ref` / `environment_ref` / `period`（計画の値を上書き）。
  - `exit_criteria[]`：`criterion_id`、`metric`（`pass_rate` / `executed_rate` / `fail_count` / `unexecuted_count` / `review_completion` / `cleanup_complete`）、`operator`、`threshold`、`source_ids[]`。
- `scope`（計画なしの直接依頼）：`scope_ref`、`discovery_roots[]`、`build_ref`。
- `retrievals[]`：`source_id`、`status`（`complete` / `partial` / `failed` / `not_attempted`）、`pagination_complete`、`permission_ok`、`source_revision`、`retrieved_at`、`records[]`。
  - `records[]`：`result_ref`、`unit_ref`、`unit`、`state`（PASS / FAIL / 未実行 / SKIP / 判定不能 / blocked、静的は`reviewed` / `not_reviewed` / `tool_failed`）、`build_ref`、`environment_ref`、`executed_at`（実行・レビュー時刻。対象期間の照合に使う）、`result_finalized`、`cleanup_status`、`attempt_no`（attempt単位。整数）。静的sourceのfindingは`unit=finding`のrecord。
- `current_source_revisions`（source id→現在revision）、`current_plan_revision`（取得できなければ未指定。未確認として扱う）、`defects[]`（`candidate_ref`、`external_issue_ref`）。

## 出力（`report_snapshot`）

`artifact_type`、`schema_version=1`、`snapshot_ref`（`RPT-`+snapshot本体全体のhash）、`population_basis`（`planned` / `unknown_direct_request`）、`plan_ref` / `plan_revision` / `plan_approval_state` / `plan_currentness`（`current` / `superseded` / `unverified` / `not_applicable`）/ `period`、`scope_ref`、`build_ref`、`sources[]`、`unplanned_retrieved_sources[]`、`by_unit`、`overall{complete, population_known, pass_rate=null}`、`exit_criteria[]`、`exit_judgement`（`satisfied` / `unsatisfied` / `undetermined`）、`defect_projection{read_only=true}`、`release_decision`、`issues[]`。

`sources[]`：`source_id`、`kind`、`unit`、`planned_total`、`retrieved_total`、`unretrieved`、`missing_unit_refs[]`、`unplanned_unit_refs[]`、`conflicting_unit_refs[]`、`records_digest`、`excluded[]`（理由：`build_mismatch` / `environment_mismatch` / `record_source_revision_mismatch` / `period_mismatch` / `period_unverified`）、`counts{raw state→件数}`、`source_revision`、`retrieved_at`、`empty_set`（`confirmed_no_target` / `unknown_not_zero` / `not_empty`）、`closure{population_complete, source_current, results_observable, cleanup_closed}`、`complete`、`issues[]`、実行方式は`pass_rate` / `executed_rate` / `unexecuted` / `retrieved_only_pass_rate`、静的方式は`review_completion` / `finding_count` / `zero_findings_claim_allowed`。

## 保存・履歴

報告snapshotは、source revisionに紐づくimmutableなsnapshotとして案件の保存先へ保存する。新規はprovider-nativeなcreate-if-absent、保存後に独立readbackを必要とする。同じ`snapshot_ref`の再保存は同一内容の確認とし、上書きしない。保存provider・承認が未選定の場合は保存をblockedにし、集計結果の提示までは続行できる。他ownerの正本（計画、元結果、欠陥）を複製して第二の正本にしない。
