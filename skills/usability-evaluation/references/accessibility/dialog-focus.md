# Reference index

## Dialog Focus and WCAG 2.2
<!-- reference-entry-id: REF-0002 -->

### Normative success criteria
For sequential navigation where order affects meaning or operation, WCAG 2.2 SC 2.4.3 requires focus order to preserve meaning and operability. SC 2.4.7 requires a visible keyboard focus indicator for keyboard-operable interfaces. SC 2.4.11 (AA) requires that a keyboard-focused component not be entirely hidden due to author-created content. SC 4.1.2 (A) covers name, role, and value for user interface components. Apply each criterion only when its stated conditions apply and keep the criterion's conformance level visible.

### Modal interpretation
WAI's Understanding guidance says a properly constructed modal takes and maintains focus, preventing interaction outside until dismissal; in that case the focused component is visible and SC 2.4.11 passes. An overlay that allows focus to move behind it while hiding that component is at risk. The informative explanation does not expand or replace the normative SC.

### Evidence boundary
Use DOM/accessibility evidence for the computed role/name and structural semantics, keyboard observations for focus order/entry/containment/return, and screenshots for visible focus and overlay occlusion. Do not infer keyboard behavior from a static screenshot or infer a conformance result from the pattern label alone. This focused entry does not constitute a WCAG conformance evaluation.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-006-ITEM-0002 | normative | WCAG 2.2 Recommendation; SC 2.4.3, Level A; checked 2026-09-28 | Applies when sequential focus order affects meaning or operability; relevant to observed dialog entry, sequence, and return when those conditions hold. |
| SRC-006-ITEM-0003 | normative | WCAG 2.2 Recommendation; SC 2.4.7, Level AA; checked 2026-09-28 | Applies to keyboard-operable UI; assess whether the keyboard focus indicator is visible in the tested dialog state. |
| SRC-006-ITEM-0001 | normative | WCAG 2.2 Recommendation; SC 2.4.11, Level AA; checked 2026-09-28 | Applies when a UI component receives keyboard focus; assess whether author-created content entirely hides it, including when focus can leave an overlay. |
| SRC-006-ITEM-0004 | normative | WCAG 2.2 Recommendation; SC 4.1.2, Level A; checked 2026-09-28 | Applies to user interface components; evaluate programmatically determinable name, role, and state/value where applicable. |
| SRC-013-ITEM-0001 | informative | WAI Understanding WCAG 2.2 SC 2.4.11; checked 2026-09-28 | Interpretive support for SC 2.4.11 modal focus behavior; informative guidance, not a substitute for the Recommendation. |
