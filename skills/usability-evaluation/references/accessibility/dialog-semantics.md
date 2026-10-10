# Reference index

## Dialog Semantics in Web Content
<!-- reference-entry-id: REF-0004 -->

### WAI-ARIA dialog role
The WAI-ARIA 1.2 `dialog` role identifies a descendant window. Authors MUST give a dialog an accessible name. Authors SHOULD ensure it has a focusable descendant, place focus in it when displayed, and manage focus for modal dialogs. `aria-modal` is a supported property of the role; its presence does not itself implement modal focus handling or make outside content non-interactive.

### Native HTML mapping
In current ARIA in HTML, the `<dialog>` element has an implicit `dialog` role. The author-conformance table allows `alertdialog`; explicitly specifying the same `dialog` role is allowed but not recommended. The table also permits global ARIA and properties applicable to the dialog role. Preserve native HTML semantics and evaluate the actual accessible name, state, and interaction instead of requiring redundant ARIA.

### Evaluation use
Treat WAI-ARIA and ARIA in HTML as normative semantics/author-conformance sources. APG remains informative guidance about authoring patterns. Verify computed role and accessible name from DOM/accessibility evidence; verify modal focus behavior separately through interaction evidence.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-010-ITEM-0001 | normative | WAI-ARIA 1.2 Recommendation; published 2023-06-06; checked 2026-09-28 | Applies to custom or native web dialog semantics; MUST accessible name and SHOULD focus-management guidance retain their respective strength. |
| SRC-009-ITEM-0002 | normative | ARIA in HTML Recommendation; current version dated 2026-08-11; checked 2026-09-28 | HTML author-conformance row for `<dialog>` and its implicit role / allowed ARIA; native role mapping is not a requirement to add a redundant explicit role. |
