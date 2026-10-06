# Authority-backed business outcome

Authority AUTH-15 states that a booking confirmation must identify the selected date and location. The booking flow remains technically operable, but step 2 shows Tuesday / Tokyo while the final summary shows Wednesday / Osaka. Immutable browser observations contain both rendered states and selected control values. The detailed TC passes because it asserted only that a confirmation page loaded.

For this semantic fixture only, the stable references for the already-described input are:

- Target: `TARGET-CASE-012` (the selected booking date and location carried into confirmation).
- Evidence: `EVIDENCE-CASE-012-STEP-2` and `EVIDENCE-CASE-012-FINAL-SUMMARY` (the immutable observations and selected values described above).
- Existing PR #13 Finding, if a distinct corrective action is required: `FINDING-CASE-012`.

These are synthetic, case-local identifiers. AUTH-15 is the applicable project Authority.
