# Eval Input

## Current package

- UI package ref: `artifact://ui-target/checkout`
- Package version: `v12`; update snapshot is available from the package writer's `inspect` operation.
- `SCOPE-004` has UI operations `UIOP-012` and `UIOP-013`.
- `UIOP-012` targets `PAGE-008`; `PAGE-008` has parent structure `NAV-002`.
- `UIOP-013` targets `DIALOG-004`.
- Current package text places these rows in `02_behavior_and_business_rules.md` at lines 44 and 51, `01_ui_structure_and_navigation.md` at lines 27, 8, and 36, and `00_scope_and_context.md` at line 19.
- Feature artifact `artifact://feature/checkout`, revision `feature-r3`, explicitly maps `FEATURE-021` to `SCOPE-004`.
- No row was changed in the current package.

## Request

Show the UI source locations for this feature and explain what has to be rechecked after an edit.
