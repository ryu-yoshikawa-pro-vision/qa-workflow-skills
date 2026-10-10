# Case E: random sample

structured sampleの10%要件、unique、non-overlap、selection methodを満たす。

This synthetic case has ten distinct current structured sample refs: `STRUCT-E-001` through `STRUCT-E-010`, each with a different target/state identity. The current complete finite candidate inventory contains those ten rows and three additional distinct rows: `CANDIDATE-E-011` (`target=TARGET-E-11`, `state=default`), `CANDIDATE-E-012` (`target=TARGET-E-12`, `state=default`), and `CANDIDATE-E-013` (`target=TARGET-E-13`, `state=default`). Inventory evidence is `EVD-CASE-E-COMPLETE-INVENTORY`; acquisition provenance is `ACT-CASE-E-CRAWL`, completed for the full declared finite inventory on `2026-10-01`. The structured sample and candidate identities do not overlap. Use current production random-selection processing; no selection seed or preferred candidate is supplied. These identities and records are synthetic fixture inputs, not product evidence.

The accompanying `input-data.json` supplies target/state source rows for all ten structured refs and all three candidate refs. Materialize the sample identity runtime from those rows, derive the candidate-population fingerprint from the helper-produced candidate identities and supplied acquisition provenance, and preserve the exact production selector output and subsequent validation result. The sidecar contains no selected random sample.
