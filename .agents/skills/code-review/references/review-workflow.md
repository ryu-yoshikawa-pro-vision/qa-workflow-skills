# Review workflow

1. Read the request and plan, then compare the complete diff with the target branch.
2. Trace changed behavior through callers, consumers, validators, tests, and CI.
3. Check that the diff preserves declared runtime, artifact, evaluation, and repository contracts.
4. Verify important claims with focused commands or source evidence. Distinguish defects from uncertainty.
5. Report only actionable findings caused by or exposed by the change.

For each finding include severity and concise title, file and line, concrete evidence, user or system impact, and a focused repair direction.

Use Critical for an immediate severe risk, High for a serious defect, Medium for a meaningful bounded defect, and Low for a minor correctness issue. Do not invent findings to fill a category. If no findings remain, state that directly and list important validation limits.
