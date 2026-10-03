# Reference index

## Accordion and Disclosure
<!-- reference-entry-id: REF-0016 -->

### Purpose and applicability
An accordion is a set of section controls that reveal or hide associated content. A disclosure is a single control that shows or hides a section. Similar appearance does not decide the pattern: use the content structure, task, and need to compare sections.

### Interaction and evidence
Use DOM/accessibility evidence for the button, expanded state, and content relationship; use a keyboard trace for activation and Tab order. APG guidance describes typical Enter/Space activation, while accordion implementations may differ on whether multiple panels stay open.

### Source position
APG is informative pattern advice. USWDS advice is advisory unless adopted by the project. Neither establishes that a pattern is appropriate for a given task.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-012-ITEM-0003 | informative | WAI-ARIA APG; checked 2026-09-28 | Use when a stacked set of content sections can be independently revealed or hidden. |
| SRC-012-ITEM-0004 | informative | WAI-ARIA APG; checked 2026-09-28 | Typical APG keyboard interaction; verify actual target behavior. |
| SRC-012-ITEM-0005 | informative | WAI-ARIA APG; checked 2026-09-28 | Use for a single show/hide control when the task and content relationship fit. |
| SRC-012-ITEM-0006 | informative | WAI-ARIA APG; checked 2026-09-28 | APG activation advice; verify behavior from interaction evidence. |
| SRC-001-ITEM-0002 | advisory | USWDS v3.14.0; checked 2026-09-28 | USWDS component advice; binding only if adopted. |

## Modal Dialog
<!-- reference-entry-id: REF-0001 -->

### Purpose and applicability
A modal dialog is a window over a primary application view that makes the underlying content unavailable for interaction while modal. Choose a modal only when the task calls for that interruption; a visible overlay or dialog role alone does not establish that it should be modal. Consider the task, amount of content, whether users need background context, and whether the interruption is reversible.

### Interaction and state
For a modal interaction, inspect where focus moves on opening, whether keyboard navigation remains within the dialog while it is modal, how it can be dismissed or completed, and where focus goes after dismissal. APG describes typical keyboard behavior and focus management; the initial focus target depends on content and task. Keep focus observations distinct from DOM semantics and from screenshots.

### Feedback and recovery
Make the dialog purpose and consequential choices understandable in context. Check whether an exit, cancel, or recovery path is apparent when the task allows one. A long or complex task may be easier to complete in a page or non-modal pattern. These prompts support expert review; APG guidance is informative and USWDS guidance is advisory unless the project adopts USWDS.

### Visual review
Use screenshots to inspect dialog bounds, hierarchy, readable content, overlay, visible actions, and whether the currently focused component is visibly obscured. A screenshot cannot establish the accessible name, focus order, focus containment, or keyboard operation; use DOM/accessibility and interaction evidence for those claims.

### Evaluation cautions
Confirm target purpose, current state, keyboard/focus observations, visual presentation, and applicable project Authority before judging. Do not infer usability from a role or a sample implementation checklist. Do not treat APG or USWDS recommendations as project requirements without applicable authority.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-012-ITEM-0001 | informative | WAI-ARIA APG Dialog (Modal) pattern; checked 2026-09-28 | Web dialog purpose and modal behavior guidance; informative pattern advice, not the sole normative implementation contract. |
| SRC-012-ITEM-0002 | informative | WAI-ARIA APG Dialog (Modal) pattern; checked 2026-09-28 | Typical keyboard and focus behavior for modal dialogs; initial focus depends on dialog content and task. |
| SRC-001-ITEM-0001 | advisory | USWDS v3.14.0; page updated 2026-08-18 | USWDS-specific modal component use guidance; advisory for products that have not adopted USWDS. |

## Tabs
<!-- reference-entry-id: REF-0017 -->

### Purpose and applicability
A tabs widget presents layered panels with one associated panel active at a time. Determine whether the content is mutually selectable panels, a sequence, a navigation hierarchy, or information that should be visible together. Visual similarity alone does not establish applicability.

### Interaction and state
Use DOM/accessibility evidence for tablist, tab, tabpanel, selected state, and relationships. Use keyboard evidence to determine arrow navigation and whether activation is automatic or manual. Automatic activation is APG advice when the panel appears without noticeable latency.

### Limits
Do not require ARIA tab semantics for unrelated navigation links. APG guidance does not replace normative WCAG evaluation.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-012-ITEM-0007 | informative | WAI-ARIA APG; checked 2026-09-28 | Use when layered panels are selected within a tabs widget. |
| SRC-012-ITEM-0008 | informative | WAI-ARIA APG; checked 2026-09-28 | Use to review the widget keyboard model; do not infer it from screenshots. |
