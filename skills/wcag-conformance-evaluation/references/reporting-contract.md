# Reporting Contract

Step 5.1 report closure tracks each Step 1–4 outcome, every not-satisfied conformance requirement and Success Criterion example, any requested all-occurrence coverage, and accessible report output. Do not collapse results into an aggregate score. Derive a non-empty `required_steps` list from current applicability decisions; each listed step must be `complete`, while `not-applicable` is only for a step excluded by those decisions. When Step 4.2 is required, pass the exact current `criterion_evaluation_ref` set from the criterion plan as `required_criterion_evaluation_refs`; `close-report` blocks missing/extra results and any `undetermined`, stale, or unknown result.

The Random Sample section preserves the target and actual counts, selection method, exact selected sample refs from the machine selector, selection status, and exhaustion or blocked reason. When no sample was selected, render `None selected` and retain the helper's closure status and evidence.

Step 5.2 Evaluation Specifics is optional and stores safe archive/evidence refs, path, settings/actions, tool/browser/AT versions, and method at the correct evaluation/sample/check scope. Do not store passwords, tokens, cookies, storage state, or unnecessary personal data.

Step 5.3 Evaluation Statement is WCAG 2.2 only. Full requires every nonoptional methodology requirement, every selected sample at target level, and owner commitment. Partial additionally requires every nonconforming area to be explained by third-party content or lack of accessibility support for languages. WCAG 2.0 and 2.1 reports do not include this Evaluation Statement.

A WCAG Conformance Claim requires full-scope claim evidence and required fields; representative samples alone are insufficient. The claim URI comes from the target-version catalog. A third-party monitoring/repair full claim additionally requires all affected pages to be identifiable, monitoring capability, and repair within two business days. A Statement of Partial Conformance is a separate type for third-party content or language and follows the canonical wording in the report contract.

Step 5.5 EARL JSON-LD is generated only when requested. Use stable evaluation/result IRIs, canonical Success Criterion URI, fixed graph shape and byte serialization, and the fixed outcome mapping. A complete criterion with no applicable population maps to `earl:inapplicable`; applicable `satisfied` maps to `earl:passed`. No other output format renderer is added.
