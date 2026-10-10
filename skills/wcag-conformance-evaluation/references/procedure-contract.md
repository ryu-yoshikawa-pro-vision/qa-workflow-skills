# Procedure Contract

Each supported Success Criterion has a criterion-specific semantic procedure and the finite machine/manual/AT/external procedures assigned by `_05i`. The versioned `wcag-semantic-contracts.json` binds a contract to each exact WCAG version and criterion. The procedure catalog is a finite inventory; it does not restrict an evaluator from discovering a separate usability/business-flow concern, which must be routed outside the WCAG result.

Machine procedures consume typed probe results. They own fixed numeric comparisons, set closure, enum decisions, applicability transitions, and browser-field derivation. The formal Skill does not call sibling Skill code to obtain a probe. `usability-inspection` is the browser owner and has a separate finite `wcag-machine-probe-catalog.json`; repository contract tests compare formal required probe keys with that catalog.

Semantic procedures preserve applicability, exception basis, decision reason, evidence, uncertainty, and additional observation draft. Additional observation cannot add or remove a required criterion or procedure. It uses the current fixed observation contract and returns to the same browser owner. Same request identity and evidence fingerprint closes as no-progress.

AT applicability decisions precede AT execution and final semantic evaluation; the decision cannot depend on an AT or final criterion result. External-evidence procedures are optional: only current evidence matching scope and environment can make them applicable. Absence or stale evidence closes the external procedure as not applicable while other required procedures continue. Conditional manual fallback activates only from the catalog's fixed machine limitation codes.
