# 判定根拠

## Source of Truth

- The requested package is a maintained UI target analysis, so the mode applies even though the scope is small. It can finish at spec-analysis; test-analysis is not required.
- The account edit operation is a required UI scope. Represent the account page and edit dialog as UI structures, and treat saved / validation-error state as a state axis rather than inventing a separate screen for each state.
- Model the user intent and the successful name update as a User Story, Use Case, Behavior, and Acceptance Criterion. The exceptional validation behavior is represented separately when it has distinct expected behavior.
- The input identifies a FIELD rule (1–40 characters) and the save flow. Preserve these in structured domain rows and link them explicitly to relevant behavior / AC rows. Do not infer links from shared scope or page alone.
- The overlength error wording is an UNKNOWN that blocks only the behavior / AC depending on that wording. Do not fabricate an exact message or turn the issue into a non-applicable scope.
- The existing CSV download is simple download behavior. It does not trigger an export-generation / transformation requirement, so it does not justify making the conditional 04 file required.

## Allowed variation

- IDs and prose may differ while stable references, semantic responsibilities, status, and package applicability remain consistent.
- The error behavior may be blocked while unaffected account behavior remains current.

## Prohibited

- Starting test-analysis or adding concrete test data, exact boundary examples, or case steps.
- Omitting the FIELD / FLOW semantics by leaving them only in extension prose.
- Marking the account scope not applicable because one error detail is unknown.
- Treating the simple download as a generated export.
