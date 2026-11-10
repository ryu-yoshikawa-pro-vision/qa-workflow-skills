# Defect management output

正規machine artifactはMarkdown内にJSON code blockをちょうど1つ置きます。`artifact_type`は`candidate_assessment` / `external_operation` / `fix_verification` / `tracking`のいずれかで、`scripts/defect_runtime.py`の判定結果をそのまま含めます。LLMが判定を補完・上書きしません。

```json
{
  "artifact_type": "candidate_assessment",
  "schema_version": "1",
  "candidate": {
    "candidate_ref": "DEFC-...",
    "candidate_state": "needs_owner_analysis",
    "status": "returned",
    "reasons": ["cause_unconfirmed"],
    "return_to": { "owner": "test-execution" },
    "automatic_registration": false,
    "formal_defect": false
  }
}
```

## artifact種別ごとの必須key

| `artifact_type`        | 必須key                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `candidate_assessment` | `candidate_input{owner_skill, cause_status, basis_ref, basis_revision, evidence_refs[], result_finalized}`、`candidate`（`assess-candidate`の出力）                                                                                                                                                                                                                                                                                    |
| `external_operation`   | `plan`（`plan-operation`の出力）、`context{now, candidate_state, write_permission, atomic_dedupe, conditional_update, duplicate_check, issue_revision_fresh, observed_target_ref, fix_target_ref, fix_verification, approval{source, authentication_verified, principal, role, policy_revision, issued_at, expires_at, binding_matches, revoked}}`、実施した場合は`outcome`（`record-outcome`の出力に`readback_verified`を加えたもの） |
| `fix_verification`     | `request`（`fix-request`の出力に`original_owner_skill`と`change_refs`を加えたもの）、結果がある場合は`result`（`fix-result`の出力に`owner_skill` / `target_ref` / `actual_start_confirmed` / `executed_targets`を加えたもの）                                                                                                                                                                                                          |
| `tracking`             | `record`（`submission` / `external_confirmation` / `fix_verification`）、`closure`（`closure`の出力）                                                                                                                                                                                                                                                                                                                                  |

`context`は`plan-operation`へ渡した入力の事実（承認の照合結果・サービスの能力・Issueの鮮度）をそのまま示し、判定と矛盾する事実を書きません。
