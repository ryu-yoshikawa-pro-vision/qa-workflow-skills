# Case AG: required criterion execution coverage

The source observation and presentation-condition facts needed to materialize the sample and variation identities are in `input-data.json`. Treat them as source evidence; generate identity fingerprints and canonical references through the production helpers.

target WCAG version / levelのrequired Success Criterion集合を生成し、1 criterionのevaluation rowを欠落させる。

Synthetic evaluation target is WCAG `2.2` level `AA`, sample `SAMPLE-CASE-AG-001`, variation `VAR-CASE-AG-001`, current baseline `BASELINE-CASE-AG`, and evidence set `EVD-CASE-AG-CURRENT`. The supplied criterion-execution snapshot reports complete current results for every required criterion except one criterion whose current evaluation row is absent. That omitted criterion has no supported ACT Rule in the current catalog; its required semantic/manual or assistive-technology procedure is also not recorded as complete. All other supplied rows are satisfied and current. Do not infer that the missing criterion is satisfied or omit it from the static expected set. The fixture is synthetic.

`SAMPLE-CASE-AG-001` and `VAR-CASE-AG-001` identify the source records, not generated canonical references. `input-data.json` supplies those source facts and the current criterion-result snapshot; derive canonical sample and variation identities through the production helpers before checking coverage.
