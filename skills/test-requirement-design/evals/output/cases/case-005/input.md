# Evaluation Input

Mode: direct test-requirement design.
Scope: password-reset token lifecycle.

## Current Effective Authority
- `SPEC-902` (revision `spec-r1`): After a password change succeeds using a reset token, that token becomes invalid. A reset token cannot authorize a second password change.

## Current Product Risk
- `RISK-902`: Reusing a reset token may allow an unintended second password change. Current risk level: `中`. Risk assessment is current; the rationale is pending periodic review.

## Scope and Instructions
Create test requirements at the service/API level. Keep each requirement at the verification-responsibility level; do not invent token lifetimes, UI wording, or rate limits. Keep any qualification about the supplied risk assessment outside the machine-readable priority value. Use the skill output template.
