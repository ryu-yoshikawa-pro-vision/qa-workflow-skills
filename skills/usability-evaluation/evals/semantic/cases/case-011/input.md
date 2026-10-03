# Additional observation and ownership

A test-execution Activity owns a saved form submission. Existing evidence shows the initial value and a successful TC assertion, but does not show the final rendered confirmation text. The confirmation value is necessary to judge whether the displayed state matches the submitted value. The same browser session is owned by test-execution.

Deterministic semantic-fixture references:

- Target: `TARGET-FORM-SUBMISSION-001` (saved form submission).
- Scope: `SCOPE-FORM-SUBMISSION-001` (the form-submission confirmation state).
- Current test-execution Activity: `ACTIVITY-TEST-EXECUTION-001`.
- Existing evidence: `EVIDENCE-INITIAL-VALUE-001` (the initial value) and `TEST-RULE-RESULT-001` (the successful TC assertion).

These identifiers exist only in this semantic fixture; they do not describe a real external product or account.
