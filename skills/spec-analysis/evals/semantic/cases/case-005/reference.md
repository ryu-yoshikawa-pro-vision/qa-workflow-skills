# 判定根拠

## Source of Truth

- Reopen the same deactivation issue as `UNK-003`; the resolver expiration invalidates its prior resolution but does not change the issue identity.
- Allocate a distinct new UNKNOWN for audit-report access. Do not reuse `UNK-003` for this separate issue.
- Preserve the resolved history for `UNK-003` and its current reopened row consistently. A prior resolution is historical and is not current authority.
- Do not retire `FIELD-006` because no semantic removal was requested.
- Saving this persistent package update advances v03 to v04. The current change summary must describe the reopen and new UNKNOWN.

## Prohibited

- Keeping `UNK-003` resolved after the resolver basis expires.
- Treating row absence or resolver expiration as an implicit retirement.
- Creating an additional UNKNOWN for the same owner-deactivation issue.
- Reusing a historical resolved ID for a semantically different question.
