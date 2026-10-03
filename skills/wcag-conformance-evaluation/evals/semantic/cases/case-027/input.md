# Case Y: EARL machine-readable report

Step 5.5を要求し、`satisfied / not-satisfied / undetermined` のformal resultを含む。

The synthetic formal result set is for WCAG `2.2` level `AA`, evaluation `EVAL-CASE-Y`, sample `SAMPLE-CASE-Y-001`, and current evidence refs `EVD-CASE-Y-1` through `EVD-CASE-Y-3`. The current criterion-result artifact contains one `satisfied` result for SC `1.1.1`, one `not-satisfied` result for SC `1.4.3`, and one `undetermined` result for SC `2.4.7`; each has a unique result ref, current freshness, procedure provenance, and evidence or limitation. The human-readable report contains those same three criterion result refs and no additional criterion assertions. The evaluation/assertor identity is `EVAL-CASE-Y`. These are synthetic input results; the serializer must produce the machine-readable representation from the current formal rows.

The accompanying `input-data.json` contains the exact current formal rows, helper-produced sample/variation identity fingerprints, and report identity needed to serialize the result set. Use the supplied rows as input to the production EARL serializer; it contains no EARL graph or expected JSON-LD output.
