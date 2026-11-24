# Defect Management data contract

JSON keyの値は英小文字のenumとし、人間向け説明は日本語で書く。すべて未信頼入力として検証する。

## `candidate`入力

| key                                          | 内容                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| `source_kind`                                | `FAIL` / `Observation` / `Finding`                                       |
| `owner_skill`                                | 元結果を持つ実行owner                                                    |
| `run_ref` / `result_ref` / `attempt_ref`     | 元runの参照                                                              |
| `scope_ref` / `environment_ref`              | 対象scope・環境                                                          |
| `target`                                     | `{kind: build \| source_revision, ref}`                                  |
| `symptom` / `reproduction` / `actual_result` | 観測事実                                                                 |
| `expected_result`                            | `{text, basis_ref, basis_revision}`。根拠なしは`null`                    |
| `evidence[]`                                 | `{ref, revision, sensitivity}`                                           |
| `cause`                                      | `{status: confirmed \| hypothesis \| unknown, confidence, analysis_ref}` |
| `result_finalized` / `cleanup_status`        | 元結果の確定とcleanup                                                    |

## `candidate`出力

`status`（`ready` / `returned` / `blocked`）、`candidate_ref`（`DEFC-`+hash）、`candidate_state`（`ready_for_external_handoff` / `needs_owner_analysis` / `needs_spec_basis`）、`reasons[]`、`return_to`（`owner` / `spec`）、`automatic_registration=false`、`formal_defect=false`。

## 外部操作

- `operation`：`create` / `comment` / `update` / `link` / `close` / `reopen`。
- `operation_id`：`DEFOP-`+hash（候補ref・操作・Issue ref・expected revision・対象targetの決定論的identity）。
- `approval`：`source=trusted_approval_service`、`authentication_verified=true`、`authenticated_by`、`principal`、`role`、`policy_revision`、`issued_at`、`expires_at`、`revoked`、および`operation` / `candidate_ref` / `scope_ref` / `artifact_revision` / `target_ref` / `service_ref` / `issue_ref` / `issue_revision`。
- `service`：`service_ref`、`write_permission`、`atomic_dedupe`、`conditional_update`。
- 判定結果：`candidate_ref`、`issue_ref`（更新系）、`decision`（`allow` / `blocked` / `read_only` / `reconfirm` / `reconcile_first` / `already_applied`）、`reasons[]`、`auto_retry_allowed`、`requires_readback`。
- 結果記録：`status`（`applied` / `unknown` / `conflict` / `failed` / `not_attempted`）、`external_update_performed`、`external_issue{issue_ref, revision, retrieved_at}`。
- 前回操作：`prior_operations[]`は`{operation_id, status: applied | unknown | started | failed, side_effect?}`。

## 修正確認

- 依頼：`status`（`request_ready` / `blocked`）、`request_ref`、`candidate_ref`、`send_to`（元owner）、`observed_target_ref`、`fix_target_ref`、`verification_targets[]`（`ref`・`revision`・`current`）、`regression_selection_owner=regression-testing`、`notice_is_confirmation=false`。
- 結果（ownerの結果は`request_ref`・`owner_skill`・`target_ref`・`state`・`actual_start_confirmed`・`result_finalized`・`cleanup_status`・`executed_targets[]{ref, revision}`を持つ）：`status`（`fix_confirmed` / `fix_not_confirmed` / `pending` / `rejected`）、`candidate_ref`、`verified_target_ref`、`fix_confirmed`。`executed_targets`が依頼した`verification_targets`と一致しなければ`pending`。

## 保存・履歴

候補・修正確認の依頼は成果物ownerの既存保存経路（案件の保存先）に保存する。新規はprovider-nativeなcreate-if-absent、更新はexpected revisionによる条件付き更新を必要とし、能力がなければ保存操作をblockedとする。外部Issueの正式状態は複製せず、`issue_ref`・revision・取得時点だけを保持する。保存provider・承認サービス・Issueサービスが未接続の場合、該当操作は`read_only`または`blocked`にし、仮の既定値を作らない。

## 既存契約との関係

- 実行ownerの結果・Machine Entity・`entity-state-v2`を再定義・再採番しない。
- `candidate_ref` / `operation_id`はこのSkill内の識別子で、既存TR / TC / Issue IDと衝突しない`DEFC-` / `DEFOP-`接頭辞を持つ。

## 探索Findingの入力（PR #22）

`exploratory-testing`の`defect_candidate_source()`が、`defect-management`宛の検証済みhandoffから欠陥候補の入力を作ります（`source_kind=Finding`、`owner_skill=exploratory-testing`、`run_ref=<session_ref>@<session_revision>`、`result_ref=<finding_ref>`）。対象buildと環境はCharter＋対象snapshot＋環境条件のhashを再現した値だけを使います。原因と期待結果の根拠は渡されない限り空で、本Skillの既存規則（`cause_unconfirmed`、`expected_result_basis_missing`）で元ownerまたは`spec-analysis`へ戻します。
