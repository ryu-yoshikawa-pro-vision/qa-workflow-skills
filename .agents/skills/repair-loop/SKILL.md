---
name: repair-loop
description: Use when the user explicitly asks to fix review findings, validation failures, or other concrete defects within a bounded scope. Do not use when there is no repair target.
---

# Bounded repair

Repair only supplied findings or validation failures within the Parent-approved scope. Read CODE_REVIEW.md, the applicable plan, and the repair workflow.

Classify each item as must_fix, should_fix, defer, reject, or needs_human. Explain the evidence. Repair confirmed in-scope items, run each relevant validation separately, and review the resulting diff. Do not add unrelated cleanup or expand the plan.

Stop when the approved scope is satisfied, the Parent-defined iteration limit is reached, a required decision is missing, or safe repair requires a scope change. If the Parent gives no limit, make at most three repair passes.

Do not create a separate run record or persistent report unless the user requests one. Return changed files, repairs, validation results, remaining findings, and the reason for stopping.
