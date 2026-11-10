# Test Evaluation data contract

## 入力

- `inputs[]`：`ref`、`revision`、`content_hash`（必須。ないものは未検証）、`kind`（`report` / `plan` / `defect` / `coverage` / `effort` / `history` / `handoff`）。
- `metrics[]`：`metric_id`、`axis`（`traceability` / `quality` / `efficiency` / `process` / `reusability`）、`definition_version`、`unit`、`numerator`、`denominator`、`value`、`direction`（`higher_is_better` / `lower_is_better`）、`source_refs[]`（`ref`・`revision`）、`conditions{scope_ref, environment_ref, population_ref}`、`previous{value, definition_version, unit, conditions}`、`unmeasured_reason`。
- `claims[]`：`axis`、`assertion`（`improved` / `partially_improved` / `mixed` / `worsened` / `measured` / `metric_improved`）。`metric_improved`は`metric_id`を伴い、その指標が主張の`axis`に属し、かつ改善している場合だけ採用する（別の軸の指標の改善は根拠にならない。同じ`metric_id`が複数の軸にある場合は軸ごとに判定する）。
- `improvements[]`：`improvement_ref`、`state`、`change_kind`（`plan` / `architecture` / `design`）、`scope_ref`、`proposal_revision`、`baseline_activity_ref`、`knowledge_candidate_ref`。
- 承認（`approval`）：`source=trusted_approval_service`、`authentication_verified`、`authenticated_by`、`principal`、`role`、`policy_revision`、`issued_at`、`expires_at`、`revoked`、`operation`（`adopt_improvement` / `confirm_handoff`）、`improvement_ref`または`item_ref`、`artifact_revision`、`scope_ref`、`approval_ref`。
- `handoffs[]`：`item_ref`、`receiver`、`artifact_revision`、`confirmation`（上記の承認形式）。

## 出力（`evaluation_report`）

`artifact_type`、`schema_version=1`、`evaluation_status`（`final` / `provisional`）、`raw_results_modified=false`、`release_decision=not_determined_by_this_skill`、`inputs[]`、`input_check{status, stale_refs, unverified_refs}`、`metrics[]`（評価済み指標：`status` = `measured` / `unmeasured` / `improved` / `worsened` / `unchanged` / `not_comparable`、`value`、`delta`、`reasons`）、`axes{5軸: status, trend, unresolved_metrics, metrics}`（`trend`：`improved` / `partially_improved` / `mixed` / `worsened` / `invalid` / `no_change_or_baseline` / `not_comparable` / `unmeasured`。軸のすべての指標から導出）、`invalid_metrics[]`（無効または5軸に属さない指標。`final`にできない）、`composite_score=null`、`claims[]`、`rejected_claims[]`、`improvements[]`、`improvement_summary{counts, achieved, not_complete}`、`handoff{items, closed, open_items}`。

改善のstateと証拠：`adopted`以降は`adoption_ref`、`handed_off`以降は`owner_skill` / `request_ref` / `base_revision`、`implemented`以降は`new_revision`（`base_revision`と異なる）、測定済みは`effect_metric`（`status`がstateに対応）。

## 保存・履歴

評価reportはsource revisionに紐づくimmutableなsnapshotとして案件の保存先へ保存する。更新はexpected revisionによる条件付き更新と保存後readbackを必要とし、能力がなければ保存をblockedにする。改善の採用・引継ぎ・実施の正本は各ownerの成果物にあり、本Skillはその参照とrevisionだけを保持する。
