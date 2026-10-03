# Case N: missing Success Criterion

target levelの静的expected setから1件を成果物で欠落させる。

The synthetic evaluation targets WCAG `2.2` level `AA`, sample `SAMPLE-CASE-N-001`, presentation variation `VAR-CASE-N-001`, and evidence set `EVD-CASE-N-CURRENT`. The accompanying `input-data.json` is the supplied prior criterion-result snapshot: its current target-level result rows omit one required criterion, and it does not identify a successful result for that criterion. Use the versioned catalog to derive the required set independently and preserve the missing-row condition rather than filling it with an LLM result. This is a test input, not an external conformance statement.
