# Reference index

## Accessible Names, States, and Test Methods
<!-- reference-entry-id: REF-0005 -->

### Accessible names and semantics
Use WAI-ARIA for role, naming, state, and property semantics; ARIA in HTML for HTML author-conformance constraints; and AccName for the name/description computation. Preserve normative strength and native semantics. Do not require redundant explicit ARIA when HTML provides semantics.

### Test methods stay distinct from requirements
ACT Rules Format defines a method format and outcome mapping. ACT rules are informative test methods; they do not add or replace WCAG success criteria. The All ACT Rules index is kept for navigation, but this Skill does not claim to implement every rule.

### Evidence selection
Use DOM/accessibility evidence for computed names, roles, and states; use targeted interaction evidence for behavior. A pattern label, attribute, or screenshot alone does not establish conformance.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-010-ITEM-0001 | normative | WAI-ARIA 1.2 Recommendation; checked 2026-09-28 | Normative semantics; retain the source's MUST/SHOULD strength. |
| SRC-009-ITEM-0002 | normative | ARIA in HTML Recommendation dated 2026-08-11; checked 2026-09-28 | HTML author conformance and native implicit roles. |
| SRC-007-ITEM-0001 | normative | Accessible Name and Description Computation 1.1 Recommendation; checked 2026-09-28 | Use for computed accessible-name and description questions. |
| SRC-008-ITEM-0001 | normative | ACT Rules Format 1.1 Recommendation; checked 2026-09-28 | Normative format for ACT rules, not a source of additional WCAG requirements. |
| SRC-015-ITEM-0001 | informative | WAI All ACT Rules index; checked 2026-09-28 | Navigation only; individual rules may be proposed or outside this package. |
