# Reference index

## Forms and Validation
<!-- reference-entry-id: REF-0018 -->

### Form task and labels
Use the supplied goal and project rules to assess field labels, instructions, grouping, required/optional status, and error relationships. Project Authority and applicable WCAG criteria can create binding obligations; USWDS examples remain advisory without adoption.

### Error identification and recovery
Record the observed message, which field it identifies, any correction suggestion, and whether the state can be corrected. WCAG 3.3.1 applies to automatically detected input errors; 3.3.2 addresses input labels or instructions; 3.3.3 covers known correction suggestions under its conditions. These criteria do not require one universal placement. A summary, inline messages, or both can fit the task.

### Evidence boundary
Use DOM/accessibility evidence for label and error relationships, interaction evidence for submit and recovery behavior, and screenshots for alignment or clipping. Do not infer behavior from a mockup or claim that users understood a message without user evidence.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-001-ITEM-0006 | advisory | USWDS v3.14.0; checked 2026-09-28 | Guidance on grouping, reading order, instructions, and validation alignment; binding only when adopted. |
| SRC-006-ITEM-0006 | normative | WCAG 2.2 SC 3.3.1 Level A; checked 2026-09-28 | Apply when an input error is automatically detected. |
| SRC-006-ITEM-0009 | normative | WCAG 2.2 SC 3.3.2 Level A; checked 2026-09-28 | Apply when content requires user input. |
| SRC-006-ITEM-0007 | normative | WCAG 2.2 SC 3.3.3 Level AA; checked 2026-09-28 | Apply when a known correction exists and exceptions do not apply. |
| SRC-013-ITEM-0002 | informative | WAI Understanding WCAG 2.2 SC 3.3.1; checked 2026-09-28 | Interpretive examples only; the normative requirement remains in WCAG. |
| SRC-003-ITEM-0006 | advisory | NN/g 10 Usability Heuristics; reviewed 2024-01-30, checked 2026-09-28 | A prompt to review preventable error conditions, not a binding form rule. |
| SRC-003-ITEM-0010 | advisory | NN/g 10 Usability Heuristics; reviewed 2024-01-30, checked 2026-09-28 | A prompt to review error recognition and recovery, not a claim about user rates. |

## Status and Feedback
<!-- reference-entry-id: REF-0019 -->

### Match the message to the event
Record what changed, whether action is required, when the message appears, and how long it remains available. Distinguish validation, success, warning, and system status. Presentation depends on urgency and the user's current task.

### Accessibility and visual evidence
WCAG 4.1.3 applies to status messages that meet its definition and requires programmatic exposure without focus movement. It does not require every message to be an alert. Use accessibility evidence for role/state and interaction evidence for timing/focus. Screenshots support visual prominence, clipping, and hierarchy only.

### Advisory prompts
NN/g visibility-of-status is a heuristic. USWDS Alert is a component example. Neither creates a project requirement unless adopted.

### Source Items
| Source Item Ref | Source Position | Source Status / Maturity | Applicability |
| --- | --- | --- | --- |
| SRC-001-ITEM-0003 | advisory | USWDS v3.14.0; checked 2026-09-28 | Component examples for status and validation; advisory outside adopted USWDS projects. |
| SRC-006-ITEM-0012 | normative | WCAG 2.2 SC 4.1.3 Level AA; checked 2026-09-28 | Apply to status messages as defined by the criterion. |
| SRC-003-ITEM-0003 | advisory | NN/g 10 Usability Heuristics; reviewed 2024-01-30, checked 2026-09-28 | Prompt to review visible status and feedback; not a conformance test. |
