# 判定根拠

## Source of Truth

- The approved administrator-only policy remains the Authority. Repository behavior does not amend or override it.
- The frontend permitting editors is an implementation gap against the policy. Record it as repository implementation status with the observed frontend revision and date; do not promote it to DECISION or current Authority.
- The backend observation remains tied to `api-219` / 2026-09-21. Rechecking the frontend does not refresh or replace the backend baseline.
- Keep both repositories in the package. The backend observation is evidence of an implementation check, not proof that the whole system conforms.

## Prohibited

- Rewriting the policy to allow editors because the frontend currently does so.
- Updating the backend revision or observation date without a new backend check.
- Routing this implementation difference to question-analysis as though the policy itself were ambiguous.
