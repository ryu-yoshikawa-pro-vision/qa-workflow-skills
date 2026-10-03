# Case AJ: criterion plan bypass

LLM suppliedのSuccess Criterion resultをfinal sample resultへ直接入力する。

Synthetic bypass attempt targets WCAG `2.2` level `AA`, sample `SAMPLE-CASE-AJ-001`, variation `VAR-CASE-AJ-001`, and criterion `1.4.3`. The caller supplies `result=satisfied` and explanation text directly, but the supplied row has no current criterion-evaluation ref, no complete procedure closure, and no evidence refs. A separately generated current criterion plan exists for the target version and sample; the bypass row is not part of that plan. Preserve it as untrusted semantic input and pass the case through the current production structure helper; do not use the supplied value as a final sample result. These are synthetic case facts.
