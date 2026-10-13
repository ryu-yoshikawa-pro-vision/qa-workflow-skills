---
name: feature-plan
description: Use when a request needs repository investigation and a written implementation plan before code changes, or when the user explicitly asks for a plan. Do not use for a small direct implementation request or review-only work.
---

# Feature planning

Create a repository-specific plan that another engineer can implement and verify without filling in major decisions. Read the request, relevant issue or pull request, repository instructions, current implementation, tests, CI, and PLANS.md.

Do not implement during planning. Plan-only requests may update the plan document only. Separate verified facts from assumptions. Ask the user about decisions that change scope or contracts, while continuing independent investigation.

Identify the goal, current state, existing contracts, scope, exclusions, risks, ordered implementation steps, independent validations, blocked conditions, and completion criteria. Prefer existing runtime, validators, helpers, and standard platform features.

Use assets/plan-template.md and save an agreed plan under docs/plans/ using the naming rule in PLANS.md. Link primary evidence where useful.
