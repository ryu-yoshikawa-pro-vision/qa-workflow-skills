# Dialog false-positive control

Use `assets/output-template.md` and `scripts/evaluation_structure.py`. Evaluate only the saved evidence below.

## Conditions and evidence

- Target: a native HTML `dialog` for a reversible preference change.
- User goal: choose a display density and either save or cancel.
- Saved DOM/accessibility evidence: named dialog; Save and Cancel buttons; focus enters the dialog and is contained; Escape closes it and returns focus to its opener.
- Saved screenshot: both actions are visible, neither is clipped or obscured at the supplied viewport.
- Project context: the dialog is an intentional, adopted pattern for this preference task. The task is reversible and no business rule requires a confirmation step.
- Evidence refs: `EV-101` (DOM/accessibility), `EV-102` (keyboard trace), `EV-103` (screenshot), `AUTH-101` (project context).

The dialog may look visually different from a generic modal example. Determine applicability from the purpose and behavior, not appearance alone. Do not create a problem or Finding when the evidence supports the project-specific behavior.
