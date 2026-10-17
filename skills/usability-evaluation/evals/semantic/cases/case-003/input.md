# Responsive visual issue

The saved desktop accessibility snapshot includes the primary Save action. A mobile screenshot at 320 CSS px shows the fixed footer covering the action; no mobile DOM or interaction trace is available. The task is to save a profile. References include WCAG 2.2 Reflow and a responsive layout pattern.

For this semantic fixture only, the stable references for the already-described input are:

- Target: `TARGET-CASE-003` (profile Save action at the mobile viewport).
- Scope: `SCOPE-CASE-003-REFLOW-AVAILABILITY` (whether the profile Save action remains available at the reported 320 CSS px condition).
- Evidence: `EVIDENCE-CASE-003-DESKTOP-SNAPSHOT` (desktop accessibility snapshot) and `EVIDENCE-CASE-003-MOBILE-SCREENSHOT` (320 CSS px screenshot).
- Current evidence owner: `ACTIVITY-CASE-003-TTI` (the test-target-inspection activity that captured the saved evidence).
- Existing PR #13 Finding, if a distinct corrective action is required: `FINDING-CASE-003`.

These are synthetic, case-local identifiers. They do not assert that the mobile action is operable or that WCAG 2.2 SC 1.4.10 fails; use them only to link supported observations and routing.
