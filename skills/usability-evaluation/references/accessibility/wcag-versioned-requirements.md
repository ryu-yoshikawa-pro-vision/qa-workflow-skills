# Reference index

## Versioned WCAG Requirements for UI Evaluation
<!-- reference-entry-id: REF-0006 -->

### Keep WCAG versions separate
Use the exact version and level from project Authority or the request. WCAG 2.0, 2.1, and 2.2 are separate normative Recommendations with version-specific criteria. Do not silently replace a named target with the newest version. WCAG 2.2 removed obsolete 4.1.1 Parsing. WAI overview, FAQ, and Quick Reference pages help navigate requirements but do not replace the normative version-specific Recommendation.

### UI-related criteria
This is a routing aid, not a complete procedure inventory. Apply criterion text, level, and exceptions from the selected version. Relevant areas can include contrast, reflow, text spacing, keyboard operation, focus order/visibility/obscuration, input errors, labels, component semantics, and status messages.

### Evidence and scope
Use DOM/accessibility evidence for programmatic semantics, interaction evidence for keyboard order/state transitions, and images for visible contrast, reflow, clipping, or focus visibility. A semantic UX result is not a WCAG conformance claim. Formal WCAG-EM work belongs to `wcag-conformance-evaluation`.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-004-ITEM-0001 | normative | WCAG 2.0 Recommendation; checked 2026-09-28 | Use only when WCAG 2.0 is the selected target; retain its criterion set. |
| SRC-005-ITEM-0001 | normative | WCAG 2.1 Recommendation; checked 2026-09-28 | Use only when WCAG 2.1 is the selected target; retain its criterion set. |
| SRC-006-ITEM-0014 | normative | WCAG 2.2 Recommendation, updated 2024-12-12; checked 2026-09-28 | Use when WCAG 2.2 is the selected target; it omits obsolete 4.1.1. |
| SRC-006-ITEM-0005 | normative | WCAG 2.2 Recommendation; SC 1.4.3, Level AA; checked 2026-09-28 | Apply when criterion conditions hold. |
| SRC-006-ITEM-0011 | normative | WCAG 2.2 Recommendation; SC 1.4.10, Level AA; checked 2026-09-28 | Apply the exact viewport/zoom conditions and exceptions. |
| SRC-006-ITEM-0010 | normative | WCAG 2.2 Recommendation; SC 1.4.11, Level AA; checked 2026-09-28 | Apply to visual information needed to identify components or states. |
| SRC-006-ITEM-0013 | normative | WCAG 2.2 Recommendation; SC 1.4.12, Level AA; checked 2026-09-28 | Apply specified user-applied spacing values and exceptions. |
| SRC-006-ITEM-0008 | normative | WCAG 2.2 Recommendation; SC 2.1.1, Level A; checked 2026-09-28 | Apply to functionality available through a keyboard interface. |
| SRC-006-ITEM-0002 | normative | WCAG 2.2 Recommendation; SC 2.4.3, Level A; checked 2026-09-28 | Apply when order affects meaning or operation. |
| SRC-006-ITEM-0003 | normative | WCAG 2.2 Recommendation; SC 2.4.7, Level AA; checked 2026-09-28 | Apply when a keyboard interface is available. |
| SRC-006-ITEM-0001 | normative | WCAG 2.2 Recommendation; SC 2.4.11, Level AA; checked 2026-09-28 | Check if a keyboard-focused component is entirely hidden. |
| SRC-006-ITEM-0006 | normative | WCAG 2.2 Recommendation; SC 3.3.1, Level A; checked 2026-09-28 | Apply when an input error is automatically detected. |
| SRC-006-ITEM-0009 | normative | WCAG 2.2 Recommendation; SC 3.3.2, Level A; checked 2026-09-28 | Apply when content requires input. |
| SRC-006-ITEM-0007 | normative | WCAG 2.2 Recommendation; SC 3.3.3, Level AA; checked 2026-09-28 | Apply when a known correction exists and exceptions do not apply. |
| SRC-006-ITEM-0004 | normative | WCAG 2.2 Recommendation; SC 4.1.2, Level A; checked 2026-09-28 | Apply to components under the criterion's semantic conditions. |
| SRC-006-ITEM-0012 | normative | WCAG 2.2 Recommendation; SC 4.1.3, Level AA; checked 2026-09-28 | Apply only to messages meeting the criterion definition. |
| SRC-013-ITEM-0003 | informative | WAI Understanding WCAG 2.2 SC 1.4.10; checked 2026-09-28 | Interpretive guidance only; WCAG carries the normative requirement. |
| SRC-013-ITEM-0001 | informative | WAI Understanding WCAG 2.2 SC 2.4.11; checked 2026-09-28 | Informative modal example; not a substitute for the criterion. |
