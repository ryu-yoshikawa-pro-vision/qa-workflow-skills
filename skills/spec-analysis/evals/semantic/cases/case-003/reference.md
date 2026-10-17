# 判定根拠

## Source of Truth

- The requested package is a maintained UI target analysis, so the mode applies even though the scope is small. It can finish at spec-analysis; test-analysis is not required.
- The account edit operation is a required UI scope. Represent the account page and edit dialog as UI structures, and treat saved / validation-error state as a state axis rather than inventing a separate screen for each state.
- Model the user intent and the successful name update as a User Story, Use Case, Behavior, and Acceptance Criterion. The exceptional validation behavior is represented separately when it has distinct expected behavior.
- The input identifies a FIELD rule (1–40 characters) and the save flow. Preserve these in structured domain rows and link them explicitly from the relevant Behavior / AC rows through their `関連構造ID` references. Do not infer links from shared scope, Authority, or page alone. The conditional 04 file is required because the display-name save / validation state transition is a defined flow; the direct download of an already existing CSV does not independently trigger 04.
- Keep the existing CSV download as a UI operation / Behavior / AC and represent its user-visible delivery in 05 as an INTERACT row. It is not a 04 business-flow row. The success notice is a separate 05 notification.
- The overlength error wording is an UNKNOWN that blocks only the behavior / AC depending on that wording. Do not fabricate an exact message or turn the issue into a non-applicable scope.
- The existing CSV download is a direct UI operation whose delivery belongs in 05. Do not create a 04 business-flow row for this download alone; the defined name-save / validation state flow is why 04 is applicable. The report must not be described as generated or transformed by the download action.

## Allowed variation

- IDs and prose may differ while stable references, semantic responsibilities, status, and package applicability remain consistent.
- The error behavior may be blocked while unaffected account behavior remains current.

## Prohibited

- Starting test-analysis or adding concrete test data, exact boundary examples, or case steps.
- Omitting the FIELD / FLOW semantics by leaving them only in extension prose.
- Marking the account scope not applicable because one error detail is unknown.
- Treating the simple download as a generated export.
