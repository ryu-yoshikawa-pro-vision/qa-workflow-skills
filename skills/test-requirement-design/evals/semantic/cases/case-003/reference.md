# 判定根拠

## Source of Truth

- Derive verification responsibilities from current `AC-101` / `AC-102` and preserve their IDs in `関連AC ID`. The success navigation and rejected-login state may require separate responsibilities if they are independently testable; AC-to-TR is not one-to-one.
- `AC-103` is blocked and absent from current AC Entity input. Do not create a completed TR for its unspecified error wording. If the workflow requires it to be represented, close it explicitly as blocked disposition.
- Each current AC must link to a TR or an explicit disposition. The account access risk may shape priority and depth, but it is not an expected-behavior Authority.
- Link `SPEC-101` / `SPEC-102` to the relevant requirements or explicitly disposition each. Linking an AC does not close its Authority. Keep Authority and AC closure independent.
- Requirements state what must be verified. Do not supply test users, passwords, exact error strings, field boundary values, browser steps, or a fixed condition matrix not present in the input.
- Preserve current AC Machine Entity dependency in artifact mode. AC parent chain / linked structures contribute to freshness under the artifact contract.

## Prohibited

- Dropping `関連AC ID` or linking blocked `AC-103` as current.
- Treating AC links as proof that SPEC-101 / SPEC-102 are closed.
- One-to-one mapping as an absolute rule, or an invented test condition / case.
