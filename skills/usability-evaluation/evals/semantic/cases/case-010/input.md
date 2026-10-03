# Composite concern with no applicable public reference

An Authority-backed user goal is to compare two shipping options and select one. In state A the selected option is Standard; after the address step, state B shows Express as selected while the confirmation summary says Standard. Saved evidence links both states and records the selected-control value and final rendered summary. No public pattern directly describes this cross-step inconsistency.

For this semantic fixture only, the stable references for the already-described input are:

- Target: `TARGET-CASE-010` (shipping-option selection carried through address and confirmation steps).
- Project Authority: `AUTH-CASE-010` (the Authority-backed comparison and selection goal stated above).
- Evidence: `EVIDENCE-CASE-010-STATE-A` and `EVIDENCE-CASE-010-STATE-B` (the saved states, selected-control values, and confirmation summary described above).
- Existing PR #13 Finding, if a distinct corrective action is required: `FINDING-CASE-010`.

These are synthetic, case-local identifiers. No public reference directly applies; do not add one or turn the mismatch into a standards violation.
