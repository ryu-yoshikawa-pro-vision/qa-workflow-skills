---
name: usability-evaluation
description: Evaluate a UI or design artifact against applicable UI patterns, accessibility standards, heuristics, and project context. Use for screenshots or images (including a Japanese request to evaluate an image even if its attachment is missing), Figma, specifications, or explicitly selected saved UI evidence. Route requests that require operating a live target or current browser to usability-inspection through qa-workflow.
---

# Usability Evaluation

Review the evaluation scope before producing conclusions.

1. Read [the reference index](references/index.md), then follow only the relevant pattern, accessibility, heuristic, and platform links. Do not load the whole corpus.
2. Identify the target, platform, current state, available evidence, and evaluation purpose. Use user, goal, task, success condition, and business context only when supplied by the request, project Authority, or evidence. Do not invent user research or user behavior.
3. Separate observed facts from interpretation. Cite evidence refs for facts and source item refs for reference based claims. Keep each applied source item and its position separate.
4. Distinguish normative criteria, informative pattern guidance, advisory heuristics, project Authority, and platform guidance. A public recommendation is not project binding unless the project adopted it or an applicable Authority makes it binding.
5. Use DOM/accessibility evidence for role, accessible name, states, and structure; interaction evidence for keyboard and state transitions; screenshots for visible layout, hierarchy, overlap, clipping, and focus visibility. A screenshot alone cannot establish keyboard behavior or accessible name.
6. Treat saved `test-target-inspection` / `test-execution` evidence as read-only input only when the same request, project scope, and workflow explicitly selected UI / UX evaluation. Do not operate a browser or second session. For a live interaction request, hand off to `usability-inspection` through `qa-workflow`.
7. Close every fixed top-level aspect as evaluated or out of scope with a reason. Each evaluated aspect needs one or more result rows with a permitted basis and applicable evidence.
8. Preserve test results as recorded. Do not change TC PASS / FAIL or score Product Risk. Route binding Authority conflicts to the responsible owner.
9. Create or link a PR #13 Finding only when the result requires follow-up. Keep the Finding linked to its evaluation, source items, and evidence. Do not invent Finding IDs.
10. Enter semantic decisions into the normalized input for `scripts/evaluation_structure.py`. Copy its machine-owned Markdown sections intact; do not hand-assign refs, closure rows, Finding requirements, or counts.

Use [the output template](assets/output-template.md). Record missing evidence as a limitation or undetermined result instead of guessing.
