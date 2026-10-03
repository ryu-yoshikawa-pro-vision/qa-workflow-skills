# Case AF: third-party monitored full claim

uncontrolled third-party contentを含むpageについてmonitoring / repair経路でfull conformance claimを作る。

Synthetic WCAG `2.2` level `AA` full-scope claim facts: the product's complete page scope contains `https://northstar.example.invalid/` and `https://northstar.example.invalid/catalog`; every required criterion and conformance requirement has a current satisfied result for both pages. Full-scope evidence ref is `EVD-CASE-AF-FULL-SCOPE`. Uncontrolled third-party content affects both pages; affected-page refs `PAGE-CASE-AF-1` and `PAGE-CASE-AF-2` identify all affected pages. Monitoring is available under `EVD-CASE-AF-MONITORING`, and repair evidence `EVD-CASE-AF-REPAIR` establishes removal or correction within two business days. Claim date is `2026-10-01`; relied-upon technologies are `HTML`, `CSS`, and `JavaScript`. These records are synthetic fixture data and do not support a real external claim.

The accompanying `input-data.json` contains the complete synthetic current result rows and their unique result/evidence refs for both declared URIs, plus the structured third-party monitoring/repair facts. Treat them as supplied upstream evidence and run the production Conformance Claim helper; the file contains no generated claim.
