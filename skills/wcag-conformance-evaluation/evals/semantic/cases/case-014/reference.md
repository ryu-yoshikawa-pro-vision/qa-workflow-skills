# Expected semantic contract

Use the exact WCAG `AA` Success Criterion sets from the current versioned catalogs:

- WCAG 2.0 (38): `1.1.1, 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.3.1, 1.3.2, 1.3.3, 1.4.1, 1.4.2, 1.4.3, 1.4.4, 1.4.5, 2.1.1, 2.1.2, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.2, 2.4.3, 2.4.4, 2.4.5, 2.4.6, 2.4.7, 3.1.1, 3.1.2, 3.2.1, 3.2.2, 3.2.3, 3.2.4, 3.3.1, 3.3.2, 3.3.3, 3.3.4, 4.1.1, 4.1.2`.
- WCAG 2.1 (50): `1.1.1, 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.3.1, 1.3.2, 1.3.3, 1.3.4, 1.3.5, 1.4.1, 1.4.2, 1.4.3, 1.4.4, 1.4.5, 1.4.10, 1.4.11, 1.4.12, 1.4.13, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.2, 2.4.3, 2.4.4, 2.4.5, 2.4.6, 2.4.7, 2.5.1, 2.5.2, 2.5.3, 2.5.4, 3.1.1, 3.1.2, 3.2.1, 3.2.2, 3.2.3, 3.2.4, 3.3.1, 3.3.2, 3.3.3, 3.3.4, 4.1.1, 4.1.2, 4.1.3`.
- WCAG 2.2 (55): `1.1.1, 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.3.1, 1.3.2, 1.3.3, 1.3.4, 1.3.5, 1.4.1, 1.4.2, 1.4.3, 1.4.4, 1.4.5, 1.4.10, 1.4.11, 1.4.12, 1.4.13, 2.1.1, 2.1.2, 2.1.4, 2.2.1, 2.2.2, 2.3.1, 2.4.1, 2.4.2, 2.4.3, 2.4.4, 2.4.5, 2.4.6, 2.4.7, 2.4.11, 2.5.1, 2.5.2, 2.5.3, 2.5.4, 2.5.7, 2.5.8, 3.1.1, 3.1.2, 3.2.1, 3.2.2, 3.2.3, 3.2.4, 3.2.6, 3.3.1, 3.3.2, 3.3.3, 3.3.4, 3.3.7, 3.3.8, 4.1.2, 4.1.3`.

For each version, the required Conformance Requirements are `conformance-level`, `full-pages`, `complete-processes`, `accessibility-supported-ways`, and `non-interference`. Keep each isolated evaluation tied to its named version and level; do not substitute another version or merge the sets.

This case verifies version isolation and report-section applicability. Its input contains no selected-sample result rows, procedure executions, or complete-process result evidence. A human-readable report may be materialized, but evaluation/report closure can remain unresolved or blocked for those missing facts; materialization is not a conformance result. For WCAG 2.0 and 2.1, omit Step 5.3 Evaluation Statement. For WCAG 2.2, Step 5.3 is applicable, but the input does not satisfy its generation guard, so do not issue a Statement. Do not claim external conformance.
