# Eval Input

## Existing package

- Package version: v03.
- `UNK-003` asks whether an account administrator may deactivate an organization owner. It was resolved by an approved decision, and its resolved history is present.
- `FIELD-006` represented the owner status field and remains current.
- No semantic retirement of `FIELD-006` was requested.

## New evidence

- A resolver review found that the approval used for `UNK-003` has expired. The same owner-deactivation question is unresolved again.
- A new specification also leaves unclear whether a deactivated owner can still download an audit report. This is a separate question.

## Request

Update the package using the default version policy. Preserve stable identity where the issue is the same, and keep current and resolved UNKNOWN records coherent.
