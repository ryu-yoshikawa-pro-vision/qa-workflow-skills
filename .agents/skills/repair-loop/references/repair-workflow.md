# Repair workflow

1. Confirm each target is a finding or validation failure within the approved scope.
2. Classify it as:
   - must_fix: confirmed correctness, security, data-protection, or contract failure.
   - should_fix: confirmed defect that materially weakens the requested result.
   - defer: valid issue outside this change or lower priority than the approved scope.
   - reject: not reproducible, unsupported by evidence, or not a defect.
   - needs_human: a product, policy, or scope decision is required.
3. Record the evidence and affected contract before editing.
4. Repair only must_fix and approved should_fix items. Ask the Parent when a fix changes scope or behavior.
5. Run relevant independent validations one at a time. Do not let a later success replace an earlier failure.
6. Review the full diff and report every remaining item with its status.
7. Stop at the Parent-defined iteration limit, or at three repair passes if no limit was given.
