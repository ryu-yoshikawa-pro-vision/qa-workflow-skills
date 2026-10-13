---
name: code-review
description: Use when the user asks to review code, a pull request, a plan, tests, or a change for defects. Review only; do not edit unless the user separately asks for repairs.
---

# Code review

Review the requested change against the user request, applicable plan, repository contracts, implementation, tests, and CI. Read CODE_REVIEW.md and the referenced review workflow.

Prioritize concrete correctness defects, security or data-protection issues, compatibility and regression risks, and missing tests. Support each finding with evidence and explain its impact. Use severity proportional to likely consequence.

Do not modify files during review-only work. Do not report style preferences or unrelated existing issues as findings. Do not run an external review service unless the user explicitly asks.

Return findings first, ordered by severity, with file and line references. If no actionable findings remain, say so and summarize checks and limits.
