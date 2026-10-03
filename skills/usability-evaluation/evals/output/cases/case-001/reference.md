## Evaluation Conditions

| Field | Value |
| --- | --- |
| target | {"name":"API token settings — remove dialog","ref":"TARGET-001","region":"Settings"} |
| platform | Web / Chromium fixture |
| viewport_device | 1280x720 desktop |
| locale | en-US |
| current_state | Remove API token dialog open |
| evidence_refs | ["EV-001","EV-002","EV-003","EV-004"] |
| project_authority_refs | [] |
| adopted_design_system_refs | [] |
| limitations | [] |
| user | - |
| user_goal_task_flow | Remove an API token after reviewing the consequence |
| success_condition | Understand the consequence, choose whether to proceed, and safely leave by keyboard. |
| business_outcome | - |
| business_rule | - |

## Pattern Identification

| Draft Key | Target Ref | Pattern | Purpose | User Goal Relationship | Applicability | Source Refs | Reason Not Identified |
| --- | --- | --- | --- | --- | --- | --- | --- |
| modal-pattern | TARGET-001 | Modal dialog | Temporarily place a task above the primary view while preserving a safe way to complete or leave it. | The dialog interrupts token settings to confirm a destructive action. | The task interrupts the settings view and presents a modal choice. | [{"reference_entry_ref":"REF-0001","source_item_ref":"SRC-012-ITEM-0002"}] | - |

## Evaluation Scope Closure

| Aspect Key | Aspect | Handling | Reason |
| --- | --- | --- | --- |
| purpose-understanding | 目的・理解可能性 | 対象外 | このfixtureでは評価しない |
| interaction | interaction | 今回評価する | - |
| feedback | feedback | 対象外 | このfixtureでは評価しない |
| error-prevention-recovery | error prevention / recovery | 対象外 | このfixtureでは評価しない |
| accessibility | accessibility | 対象外 | このfixtureでは評価しない |
| visual-integrity | visual integrity | 対象外 | このfixtureでは評価しない |
| cross-pattern-flow | cross-pattern / flow | 対象外 | このfixtureでは評価しない |

## UI / UX Evaluation Results

| Evaluation Ref | Aspect Key | Draft Key | Status | Finding Ref | Machine Normalized Record |
| --- | --- | --- | --- | --- | --- |
| EVAL-001 | interaction | dialog-focus | 問題を確認 | - | {"additional_observation_links":[],"applied_references":[{"authority_binding_applied":false,"project_authority_refs":[],"reference_entry_ref":"REF-0001","reference_position":"informative pattern guidance","source_item_ref":"SRC-012-ITEM-0002"}],"aspect":"interaction","aspect_key":"interaction","basis":["reference","user-goal"],"difference":"Focus escaped to an obscured background control and Escape did not dismiss the dialog.","draft_key":"dialog-focus","evaluation_ref":"EVAL-001","evidence_refs":["EV-001","EV-002","EV-003","EV-004"],"expected_characteristic":"Keyboard interaction remains within the modal dialog and provides a way to dismiss or complete the task.","expected_impact":"A keyboard user may leave the intended task context and may lack a discoverable way to leave without activating the destructive action.","finding_ref":null,"finding_required":false,"follow_up_required":false,"impact_basis":"The saved keyboard trace shows focus on the background trigger while the dialog remained open; no user frequency is inferred.","judgment_reason":"The evidence supports an interaction concern under the informative APG dialog keyboard guidance. This does not change the supplied TC PASS and is not a formal WCAG result.","measurement_refs":[],"note":"TC-001 remains PASS; this is a separate UI/UX evaluation.","observed_fact":"After Tab moved beyond the dialog, the background Create API token button became active while the dialog remained open. Escape left the dialog open.","observed_user_impact":null,"pattern_draft_key":"modal-pattern","pattern_or_principle":"Modal dialog keyboard interaction","project_authority_refs":[],"reference_not_used_reason":null,"requirement_check_refs":[],"routing":"test-target-inspection","status":"問題を確認","status_reason":null,"target":"Modal dialog focus and keyboard dismissal","test_rule_result_refs":["RULE-001"],"user_goal_task_flow":"Remove an API token after reviewing the consequence"} |

## Evaluation Summary

| Metric | Count |
| --- | ---: |
| evaluated_aspects | 1 |
| evaluation_count | 1 |
| finding_count | 0 |
| issue_count | 1 |
| no_issue_count | 0 |
| out_of_scope_aspects | 6 |
| out_of_scope_result_count | 0 |
| pattern_identification_count | 1 |
| undetermined_count | 0 |
