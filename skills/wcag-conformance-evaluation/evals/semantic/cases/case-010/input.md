# Case H: Step 4.3 retry

random sampleから新content type / findingを検出。

The prior sampling iteration is revision `1`, with structured sample refs `STRUCT-H-001` and `STRUCT-H-002`, one current random sample `RANDOM-H-003`, and selection method `system-random finite inventory selection`. Its candidate-population fingerprint is the saved production-helper result in `input-data.json`. During Step 4.3, the random sample produced current evidence `EVD-CASE-H-PDF` for a downloadable invoice/PDF content type and a distinct Finding group `FG-CASE-H-DOCUMENT-ACCESS`. The Step 2 inventory is revised to add `VIEW-H-INVOICE` with source evidence `EVD-CASE-H-INVOICE-INVENTORY`; current candidate inventory, sample identities, and provenance are supplied by `ACT-CASE-H-INVENTORY-REV-2`. The PDF and Finding group were absent from the prior exploration and structured set. All identifiers are synthetic case-local inputs; do not infer an external product result.

The accompanying `input-data.json` contains the prior fingerprint record and current sample-identity runtime result. Use those inputs with the production Step 4.3 helper, and obtain any newly required random sample from the production random selector without a fixed seed.
