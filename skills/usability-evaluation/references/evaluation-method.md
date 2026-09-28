# Evaluation Method

## Scope

Evaluate the stated UI / UX question against target purpose, supplied context, available evidence, applicable project Authority, and relevant reference entries. Fix the set of top-level aspects before interpreting findings: purpose/understanding, interaction, feedback, error prevention/recovery, accessibility, visual integrity, and cross-pattern/flow. Mark each as evaluated or out of scope; explain every exclusion.

## Applicability

Identify a pattern by its purpose and interaction model, not visual resemblance alone. Record why the selected source applies to this target and preserve its source position. A pattern example is not the only valid implementation. Keep project binding, normative criteria, informative pattern advice, and advisory heuristics distinct.

## Evidence and interpretation

Record observable facts separately from interpretation. Use DOM/accessibility evidence for semantic claims, interaction traces for behavior, and screenshots for visible presentation. Use task/user/success context only when supplied. A missing observation is a limitation, not a presumed failure or success.

## Result and follow-up

Use the contract statuses `問題を確認`, `問題なし`, `判定不能`, and `対象外`. A problem result records evidence and an impact basis. `判定不能` and `対象外` include a reason. Create or link a PR #13 Finding only when follow-up is required; leave successful and excluded rows without a Finding ref. Do not rewrite test execution results or Product Risk.

## Live observation boundary

This Skill evaluates supplied artifacts and explicitly selected saved evidence. Live target operation and deterministic browser probes belong to `usability-inspection` through `qa-workflow`. Do not acquire browser ownership or run an ad hoc script here.
