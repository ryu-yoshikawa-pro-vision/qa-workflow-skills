# UI / UX Evaluation

Use `scripts/evaluation_structure.py` to materialize the five machine-owned sections below. Replace each placeholder section with the helper's rendered section without editing its rows, refs, normalized records, or counts. Put semantic decisions in the helper input; never fill machine-owned values by hand.

## Evaluation Conditions

<!-- Replace with the complete Evaluation Conditions section from evaluation_structure.py. -->

Required context includes target and region, platform, viewport/device, locale, current state, evidence refs, project Authority and adopted Design System refs, limitations, and any supplied user/goal/task, success condition, business outcome, or business rule.

## Pattern Identification

<!-- Replace with the complete Pattern Identification section from evaluation_structure.py. -->

Include source entry and source item refs for each identified pattern. Record applicability and purpose; record why no pattern was identified where that is the semantic conclusion.

## Evaluation Scope Closure

<!-- Replace with the complete Evaluation Scope Closure section from evaluation_structure.py. -->

The helper emits the fixed aspect rows and requires an exclusion reason for each aspect marked out of scope.

## UI / UX Evaluation Results

<!-- Replace with the complete UI / UX Evaluation Results section from evaluation_structure.py. -->

Each normalized row carries observed fact, evaluation basis, expected characteristic, difference, impact and its basis, source/Authority/evidence links, additional observation ownership where needed, status, routing, and a linked Finding when required.

## Evaluation Summary

<!-- Replace with the complete Evaluation Summary section from evaluation_structure.py. -->

## Finding References

When a distinct downstream QA action requires a PR #13 Finding, link the actual ref supplied or created through the existing PR #13 artifact path. Do not use `PR #13`, `PR #13 Finding artifact`, or another contract/type label as a Finding ref, and do not invent an ID. If a required Finding cannot be linked through the existing artifact path, leave the artifact incomplete and report the blocker. An additional-observation link to the current owner is separate from a Finding. Do not create a Finding for a result marked `問題なし` or `対象外`. The evaluation's `finding_ref` is a cross-reference, not a replacement for the Finding contract.

## Limitations and Handoff

Record unobserved behavior, unavailable evidence, unresolved Authority conflict, and the responsible next owner. A live browser observation request belongs to `usability-inspection` through `qa-workflow`; saved evidence owned by `test-target-inspection` or `test-execution` remains immutable and read-only here.
